"""Everything the screens read and do. One process, no server, no open ports.

Screens never call these methods directly. They go through request(), which checks who is signed in.
"""

import csv
import html
import json
import shutil
import time
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import auth, config, db, mission
from .auth import CREW_ROLES, AuthError
from .engine.alerts import PROTOCOLS
from .live import Live, MissionClock
from .models import CheckIn
from .signals import BY_ID, DRIFT_SIGNALS, SIGNALS, SYSTEMS
from .sim.generator import CREW
from .store import Store, series_payload
from .sync.outbox import Outbox
from .sync.privacy import crew_card, ground_card
from .sync.queue import PRIORITY_LEVEL3, PRIORITY_NORMAL

TREND_DAYS = 30
CHART_SIGNALS = 3
EXPLAINER_WINDOW = 50
CALL_PACKET_KB = 32.0
STATUS_CODE = {"green": "g", "yellow": "y", "red": "r"}
EARTH_DECISIONS = {
    0: ("none", "No call needed.", "Every system is in your usual range. A summary goes to Earth every 7 days."),
    1: ("self", "Handle this on board.", "Follow the step on the alert and recheck in 48 hours."),
    2: ("crew", "Tell the Medical Officer.", "They can run the longer check on board sooner than a reply from Earth could arrive."),
    3: ("earth", "Send a priority packet now.", "Level 3 is active. Start the checklist on the alert while the packet travels."),
}
# Wearables are simulated. Each maps to the signals it would measure.
SENSORS = (
    ("Chest strap", ("resting_hr", "hrv", "ortho_rise")),
    ("Blood pressure cuff", ("bp_sys", "bp_dia")),
    ("Finger sensor", ("spo2",)),
    ("Sleep band", ("sleep_hours", "sleep_eff")),
    ("Skin temperature patch", ("temp",)),
    ("Exercise rig", ("exercise_min", "exercise_load")),
    ("Personal dosimeter", ("dose_rate",)),
)
BATTERY_DRAIN_PER_DAY = 7
BATTERY_RANGE = 80
BATTERY_CHARGING_BELOW = 30

DEMO_PIN = "2026"  # shown on the sign-in screen of the demo mission only
DEMO_PIN_ITERATIONS = 1000  # the demo PIN is public, so its hash need not be slow
DEMO_ROLES = {"cmdr": "commander", "plt": "crew", "mo": "medical", "eng": "crew", "ctl": "crew"}
DEFAULT_AUTO_LOCK_MINUTES = 5
AUTO_LOCK_CHOICES = (1, 2, 5, 10, 15, 30)
MISSION_NAME_LIMIT = 60
MAX_MISSION_DAYS = 1100
AUDIT_LIMIT = 300
IMPORT_TYPES = (".csv", ".xml", ".zip")  # CSV tables, and Apple Health exports

# Who may make which request. Everything is checked here, not only hidden on screen.
PUBLIC = {"members", "mission_info", "about"}
OWN = {  # request name -> the argument that names whose data it is
    "astronaut": "id", "system_detail": "id", "alert_detail": "id", "radiation": "id", "sensors": "id", "get_share": "id",
    "set_share": "id", "earth_decision": "id", "call_earth": "astronaut", "checkin": "astronaut", "notices": "id",
    "log_form": "id", "log_readings": "id", "entries": "id", "delete_entry": "id", "import_file": "id", "export_data": "id",
    "report": "id", "alert_action": "id", "undo_alert_action": "id",
}
MEDICAL_MAY = {"log_form", "log_readings", "entries", "delete_entry", "import_file"}  # the Medical Officer enters lab results
CREW_TIER = {"crew", "crew_view", "import_files"}
GROUND_TIER = {"ground", "packets"}
DEMO_ONLY = {"set_clock", "demo_start", "demo_next", "demo_stop", "timeline", "explainer", "results", "set_link"}
LIVE_ONLY = {"log_form", "log_readings", "entries", "delete_entry", "import_files", "import_file", "archive_mission"}
COMMAND = {
    "get_config", "put_config", "reset_config", "accounts_admin", "add_member", "update_member", "reset_member_pin",
    "unlock_member", "set_auto_lock", "audit_log", "backup", "archive_mission",
}
REQUESTS = PUBLIC | set(OWN) | CREW_TIER | GROUND_TIER | DEMO_ONLY | LIVE_ONLY | COMMAND
STATION_ROLES = {"vehicle": CREW_ROLES | {"presenter"}, "ground": {"ground", "presenter"}}


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _finite(value: float) -> float | None:
    return None if value != value else round(float(value), 3)


def _identity(who: Any) -> dict[str, Any]:
    return {"id": who.id, "name": who.name, "role": who.role, "tag": who.tag, "control": who.control}


def _merge(base: dict[str, Any], new: dict[str, Any], path: str = "") -> None:
    """Copy new settings into base. Unknown keys and wrong types are rejected."""
    for key, value in new.items():
        where = f"{path}{key}"
        if key not in base:
            raise ValueError(f"Unknown setting: {where}")
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise ValueError(f"{where} must be a group of settings.")
            _merge(base[key], value, f"{where}.")
        elif isinstance(base[key], bool) != isinstance(value, bool) or isinstance(base[key], list) != isinstance(value, list):
            raise ValueError(f"{where} has the wrong type.")
        elif isinstance(base[key], int | float) and not isinstance(value, int | float):
            raise ValueError(f"{where} must be a number.")
        elif isinstance(value, int | float) and not isinstance(value, bool) and value < 0:
            raise ValueError(f"{where} cannot be negative.")
        else:
            base[key] = value


class Vigil:
    """One mission, one clock. Every public method returns plain data for a screen."""

    store: Store
    live: Live | MissionClock
    accounts: auth.Accounts

    def __init__(self, clock: Callable[[], float] = time.monotonic, mode: str = "demo",
                 today: Callable[[], date] = date.today, wall: Callable[[], float] = time.time) -> None:
        self.clock, self.today, self.wall = clock, today, wall
        self.actor, self.actor_role = "system", "system"
        self.open(mode)

    # Which mission is open

    @staticmethod
    def mission_exists() -> bool:
        return config.MISSION_DB_PATH.exists() and db.get_setting(config.MISSION_DB_PATH, "start_date") is not None

    def open(self, mode: str) -> None:
        """Open the demo mission or the real one. They live in separate databases and never mix."""
        if mode == "live":
            if not self.mission_exists():
                raise LookupError("No mission has been set up on this computer yet.")
            self.store = Store("live", config.MISSION_DB_PATH, self.today)
            sync = self.store.cfg["sync"]
            outbox = Outbox(config.MISSION_DB_PATH, config.OUTBOX_DIR, sync["one_way_delay_minutes"], sync["bandwidth_kb_s"])
            self.live = MissionClock(self.store, self.clock(), outbox)
        elif mode == "demo":
            self.store = Store()
            self.live = Live(self.store, self.clock())
        else:
            raise ValueError(f"Unknown mission: {mode}")
        self.mode = mode
        self.accounts = auth.Accounts(self.store.db_path, self.wall)
        if mode == "demo" and not self.accounts.exists():
            self._seed_demo_accounts()

    def _seed_demo_accounts(self) -> None:
        for who in CREW:
            self.accounts.create(who.name, DEMO_ROLES[who.id], DEMO_PIN, who.prior_dose, must_change=False,
                                 member_id=who.id, tag=who.tag, iterations=DEMO_PIN_ITERATIONS)
        self.accounts.create("Presenter", "presenter", DEMO_PIN, must_change=False, member_id="presenter", tag="DEMO", iterations=DEMO_PIN_ITERATIONS)
        self.accounts.create("Flight Surgeon", "ground", DEMO_PIN, must_change=False, member_id="surgeon", tag="MCC", iterations=DEMO_PIN_ITERATIONS)

    def setup_mission(self, name: str, start_date: str, length_days: int, commander: str, pin: str, prior_dose: float = 0.0) -> dict[str, Any]:
        """Create a real mission and its first Commander, then open it."""
        if self.mission_exists():
            raise ValueError("A mission is already set up on this computer.")
        name = " ".join(str(name).split())
        if not name or len(name) > MISSION_NAME_LIMIT:
            raise ValueError(f"Give the mission a name of 1 to {MISSION_NAME_LIMIT} characters.")
        try:
            start = date.fromisoformat(str(start_date).strip())
        except ValueError:
            raise ValueError("Write the start date as year-month-day, for example 2026-11-14.") from None
        if not isinstance(length_days, int) or not 1 <= length_days <= MAX_MISSION_DAYS:
            raise ValueError(f"Mission length must be a whole number of days from 1 to {MAX_MISSION_DAYS}.")
        if start > self.today():
            raise ValueError("The start date cannot be in the future. Set the mission up on launch day or later.")
        if mission.mission_day(start, self.today()) > length_days:
            raise ValueError("That start date and length would mean the mission is already over.")
        problem = auth.pin_problem(str(pin))
        if problem:
            raise ValueError(problem)
        config.MISSION_DB_PATH.unlink(missing_ok=True)  # a half-made file from an earlier try
        accounts = auth.Accounts(config.MISSION_DB_PATH, self.wall)
        try:
            boss = accounts.create(commander, "commander", str(pin), float(prior_dose), must_change=False)
        except AuthError:
            config.MISSION_DB_PATH.unlink(missing_ok=True)
            raise
        for key, value in (("name", name), ("start_date", start.isoformat()), ("length_days", length_days),
                           ("auto_lock_minutes", DEFAULT_AUTO_LOCK_MINUTES), ("created_at", self.wall())):
            db.set_setting(config.MISSION_DB_PATH, key, value)
        db.audit(config.MISSION_DB_PATH, boss["id"], "mission_created", name, f"starts {start.isoformat()}, {length_days} days")
        self.open("live")
        return {"member": boss}

    def archive_mission(self, confirm: bool = False) -> dict[str, Any]:
        """Put the mission's file aside, so this computer can start another. Nothing is deleted."""
        if not confirm:
            raise ValueError("Confirm before archiving the mission.")
        db.audit(self.store.db_path, self.actor, "mission_archived")
        target = db.backup(self.store.db_path, config.BACKUP_DIR, f"archived-{stamp()}")
        config.MISSION_DB_PATH.unlink()
        self.open("demo")
        return {"archived_to": str(target)}

    # Sign-in. The bridge calls these with what was typed, never with a stored session.

    def sign_in(self, member: str, pin: str, station: str = "vehicle") -> dict[str, Any]:
        try:
            role = self.accounts.get(member)["role"]
            if role not in STATION_ROLES[station]:
                raise AuthError("This account signs in at Mission Control." if role == "ground" else "This account signs in on the vehicle.")
            user = self.accounts.sign_in(member, pin)
        except AuthError as err:
            db.audit(self.store.db_path, member, "sign_in_refused", station, str(err))
            raise
        db.audit(self.store.db_path, member, "signed_in", station)
        return user

    def unlock(self, member: str, pin: str) -> dict[str, Any]:
        try:
            user = self.accounts.sign_in(member, pin)
        except AuthError as err:
            db.audit(self.store.db_path, member, "unlock_refused", "", str(err))
            raise
        db.audit(self.store.db_path, member, "unlocked")
        return user

    def change_pin(self, member: str, old: str, new: str) -> None:
        self.accounts.change_pin(member, old, new)
        db.audit(self.store.db_path, member, "pin_changed", member)

    def note_session(self, member: str, action: str) -> None:
        """Record sign-out and screen locks."""
        if action in ("signed_out", "locked", "auto_locked"):
            db.audit(self.store.db_path, member, action)

    def request(self, session: dict[str, Any] | None, name: str, args: dict[str, Any]) -> Any:
        """The one door every screen uses. Checks the signed-in member, then runs the request."""
        if name not in REQUESTS:
            raise LookupError(f"Unknown request: {name}")
        if name in PUBLIC:
            return getattr(self, name)(**args)
        if session is None:
            raise PermissionError("Sign in first.")
        role, me = session["role"], session["id"]
        if name in DEMO_ONLY and self.mode != "demo":
            raise PermissionError("That is part of the demo mission only.")
        if name in LIVE_ONLY and self.mode != "live":
            raise PermissionError("The demo mission uses simulated readings. Set up a mission to record real ones.")
        if name in ("demo_start", "demo_next", "demo_stop") and role != "presenter":
            raise PermissionError("Sign in as the Presenter to play the demo.")
        if role != "presenter":
            if name in COMMAND and role != "commander":
                raise PermissionError("Only the Commander can do that.")
            if name in GROUND_TIER and role != "ground":
                raise PermissionError("That is the Mission Control view.")
            if (name in CREW_TIER or name in OWN) and role not in CREW_ROLES:
                raise PermissionError("That is for the crew on board.")
            if name in OWN:
                target = args.setdefault(OWN[name], me)
                if target != me and not (role == "medical" and name in MEDICAL_MAY):
                    raise PermissionError("You can only open your own health data. Others can choose to share theirs with the crew.")
        self.actor, self.actor_role = me, role
        try:
            return getattr(self, name)(**args)
        finally:
            self.actor, self.actor_role = "system", "system"

    def _audit(self, action: str, target: str = "", detail: str = "") -> None:
        db.audit(self.store.db_path, self.actor, action, target, detail)

    def members(self, station: str = "vehicle") -> dict[str, Any]:
        """Who can sign in here. Names and roles only."""
        allowed = STATION_ROLES.get(station, set())
        return {"members": [m for m in self.accounts.list() if m["role"] in allowed]}

    def mission_info(self) -> dict[str, Any]:
        live = self.mode == "live"
        info = self.store.info
        return {
            "mode": self.mode, "live_exists": self.mission_exists(),
            "name": info.get("name", "") if live else "Demo mission",
            "start_date": info.get("start_date") if live else None,
            "length_days": info.get("length_days") if live else self.store.mission.days,
            "day": self._day(None), "demo_pin": None if live else DEMO_PIN,
            "auto_lock_minutes": db.get_setting(self.store.db_path, "auto_lock_minutes", DEFAULT_AUTO_LOCK_MINUTES),
        }

    def _day(self, day: int | None) -> int:
        return self.store.clamp_day(day) if day is not None else self.live.snapshot(self.clock())["day"]

    # The astronaut's own screens

    def crew(self) -> dict[str, Any]:
        return {
            "crew": [_identity(w) for w in self.store.crew], "systems": SYSTEMS,
            "signals": [{"id": s.id, "name": s.name, "unit": s.unit, "system": s.system} for s in SIGNALS],
        }

    def astronaut(self, id: str, day: int | None = None) -> dict[str, Any]:
        who = self.store.who(id)
        d = self._day(day)
        run = self.store.runs[id]
        alerts = self.store.alerts(id, d)
        alert_level = {a["system"]: a["level"] for a in alerts}
        systems = []
        for key, name in SYSTEMS.items():
            today = run.systems[key][d - 1]
            systems.append({
                "id": key, "name": name, **today, "level": alert_level.get(key, 0),
                "trend": [x["score"] for x in run.systems[key][max(0, d - TREND_DAYS): d]],
            })
        return {
            "astronaut": _identity(who), "day": d, "mission_days": self.store.mission.days, "systems": systems,
            "alerts": alerts, "all_clear": not alerts, "radiation": run.radiation[d - 1],
            "learning": all(s["learning"] for s in systems),
        }

    def system_detail(self, id: str, system: str, day: int | None = None) -> dict[str, Any]:
        self.store.who(id)
        if system not in SYSTEMS:
            raise LookupError(f"No system named {system}.")
        d = self._day(day)
        run = self.store.runs[id]
        wanted = [s.id for s in DRIFT_SIGNALS if s.system == system and s.id in run.signals]
        return {
            "system": system, "name": SYSTEMS[system], "day": d, **run.systems[system][d - 1],
            "signals": [series_payload(self.store, id, sid, d) for sid in wanted],
        }

    def alert_detail(self, id: str, alert_id: str, day: int | None = None) -> dict[str, Any]:
        self.store.who(id)
        d = self._day(day)
        for past in range(d, 0, -1):
            match = next((a for a in self.store.alerts(id, past, include_hidden=True) if a["id"] == alert_id), None)
            if match:
                ids = [s["signal"] for s in match["why"]["signals"][:CHART_SIGNALS] if s["signal"] in self.store.runs[id].signals]
                return {
                    "alert": match, "closed": past != d, "day": d,
                    "charts": [series_payload(self.store, id, sid, past, 60) for sid in ids],
                    "protocol": PROTOCOLS.get(match["protocol"]), "protocol_label": PROTOCOLS["_label"],
                }
        raise LookupError("This alert is not active on this mission day.")

    def alert_action(self, id: str, alert_id: str, action: str) -> dict[str, Any]:
        if action not in ("done", "snooze", "escalate"):
            raise ValueError(f"Unknown alert action: {action}")
        d = self._day(None)
        current = self.alert_detail(id, alert_id, d)["alert"]
        self.store.record_action(alert_id, action, d, current["level"])
        updated = next((a for a in self.store.alerts(id, d, include_hidden=True) if a["id"] == alert_id), current)
        if action == "escalate":
            self.live.queue_level3(updated, d, self.clock())
        return {"alert": updated, "action": action}

    def undo_alert_action(self, alert_id: str, id: str | None = None) -> dict[str, Any]:
        if id is not None and self.actor_role not in ("presenter", "system") and not alert_id.startswith(f"{id}-"):
            raise PermissionError("You can only undo your own actions.")
        self.store.undo_action(alert_id)
        return {"undone": alert_id}

    def checkin(self, **fields: Any) -> dict[str, Any]:
        body = CheckIn(**fields)
        d = self._day(None)
        return {"day": d, "journal_score": self.store.save_checkin(body, d), "text_kept": body.keep_text and bool(body.journal)}

    def radiation(self, id: str, day: int | None = None) -> dict[str, Any]:
        self.store.who(id)
        d = self._day(day)
        series = self.store.mission.series[id]
        return {
            **self.store.runs[id].radiation[d - 1], "day": d, "mission_days": self.store.mission.days,
            "daily_dose": [round(float(v), 2) for v in series["daily_dose"][max(0, d - TREND_DAYS): d]],
            "warning_usv_h": self.store.cfg["radiation"]["dose_rate_warn_usv_h"],
        }

    def sensors(self, id: str, day: int | None = None) -> dict[str, Any]:
        """Which wearables reported today. Missing readings are real gaps in the data."""
        self.store.who(id)
        d = self._day(day)
        series = self.store.mission.series[id]
        if self.mode == "live":
            return self._sources(id, d)
        rows = []
        for index, (name, signals) in enumerate(SENSORS):
            missing = [s for s in signals if np.isnan(series[s][d - 1])]
            level = 100 - (d * BATTERY_DRAIN_PER_DAY + index * 13) % BATTERY_RANGE
            rows.append({
                "name": name, "connected": not missing, "battery": level,
                "power": "Charging" if level < BATTERY_CHARGING_BELOW else "On battery",
                "missing": [next(x.name for x in SIGNALS if x.id == s) for s in missing],
            })
        return {"day": d, "sensors": rows, "reporting": sum(r["connected"] for r in rows)}

    def _sources(self, id: str, d: int) -> dict[str, Any]:
        """Live missions: which kinds of reading arrived today, and when each last did."""
        series = self.store.mission.series[id]
        rows = []
        for name, signals in SENSORS:
            have = [s for s in signals if not np.isnan(series[s][d - 1])]
            seen = [i + 1 for s in signals for i in np.flatnonzero(~np.isnan(series[s][:d]))]
            rows.append({
                "name": name, "connected": bool(have), "battery": None, "power": "",
                "missing": [BY_ID[s].name for s in signals if s not in have], "last_day": int(max(seen)) if seen else None,
            })
        return {"day": d, "sensors": rows, "reporting": sum(r["connected"] for r in rows), "live": True}

    def get_share(self, id: str) -> dict[str, bool]:
        self.store.who(id)
        return self.store.share(id)

    def set_share(self, id: str, share_crew: bool | None = None, share_ground: bool | None = None) -> dict[str, bool]:
        self.store.who(id)
        return self.store.set_share(id, share_crew, share_ground)

    def earth_decision(self, id: str, day: int | None = None) -> dict[str, Any]:
        self.store.who(id)
        d = self._day(day)
        alerts = self.store.alerts(id, d, include_hidden=True)
        level = max((a["level"] for a in alerts), default=0)
        kind, title, detail = EARTH_DECISIONS[level]
        learning = [name for key, name in SYSTEMS.items() if self.store.runs[id].systems[key][d - 1]["learning"]]
        if level == 0 and learning:
            title = "No alert today."
            detail = ("Vigil has too few readings to judge any system yet." if len(learning) == len(SYSTEMS)
                      else f"Vigil still needs more readings for {' and '.join(learning)}.") + " A summary goes to Earth every 7 days."
        top = next((a for a in alerts if a["level"] == level), None)
        return {
            "level": level, "decision": kind, "title": title, "detail": detail, "reason": top["level_reason"] if top else None,
            "learning": learning,
            "delay_minutes": self.store.cfg["sync"]["one_way_delay_minutes"], "share": self.store.share(id),
            "preview": ground_card(self.store.runs[id], d, alerts, self.store.share(id)["share_ground"]),
        }

    def call_earth(self, astronaut: str, note: str = "") -> dict[str, Any]:
        who = self.store.who(astronaut)
        d = self._day(None)
        alerts = self.store.alerts(who.id, d, include_hidden=True)
        level = max((a["level"] for a in alerts), default=0)
        card = ground_card(self.store.runs[who.id], d, alerts, self.store.share(who.id)["share_ground"])
        now = self.clock()
        priority = PRIORITY_LEVEL3 if level >= 3 else PRIORITY_NORMAL
        packet = self.live.queue.enqueue(now, "call", who.id, f"{who.tag} call to Earth", priority, CALL_PACKET_KB, d, card | {"note": note[:280]})
        return {"packet_id": packet.id, "state": packet.state(now), "flight_seconds": self.live.queue.delay_s}

    # Crew and ground

    def crew_view(self, day: int | None = None) -> dict[str, Any]:
        d = self._day(day)
        store = self.store
        cards = [crew_card(store.runs[w.id], d, store.alerts(w.id, d), store.share(w.id)["share_crew"]) for w in store.crew if not w.control]
        watching = sum(c["max_level"] > 0 or any(s["status"] != "green" for s in c["systems"]) for c in cards)
        summary = "All crew inside their normal." if not watching else f"{watching} of {len(cards)} crew need attention."
        return {"day": d, "crew": cards, "summary": summary}

    def ground(self, day: int | None = None) -> dict[str, Any]:
        d = self._day(day)
        store = self.store
        if self.mode == "live":
            return self._ground_from_packets(d)
        cards = [ground_card(store.runs[w.id], d, store.alerts(w.id, d, include_hidden=True), store.share(w.id)["share_ground"]) for w in store.crew]
        return {
            "system_keys": list(SYSTEMS), "live": False,
            "day": d, "crew": cards, "level3": [a | {"astronaut": c["tag"]} for c in cards for a in c["level3"]],
            "packets": self.live.queue.view(self.clock()), "link_up": self.live.queue.link_up,
            "delay_minutes": store.cfg["sync"]["one_way_delay_minutes"], "flight_seconds": self.live.queue.delay_s,
        }

    def _ground_from_packets(self, d: int) -> dict[str, Any]:
        """What Earth knows is only what the packets carried. Latest status per person, Level 3 reasons."""
        outbox = self.live.queue
        assert isinstance(outbox, Outbox)  # a live mission always writes to the outbox folder
        rows = outbox.rows(200)
        latest: dict[str, dict[str, Any]] = {}
        level3 = []
        tags = {m["id"]: m["tag"] for m in self.accounts.list(include_inactive=True)}
        for row in reversed(rows):  # oldest first, so newer packets win
            if row["kind"] in ("summary", "call") and "systems" in row["payload"]:
                latest[row["member"]] = row["payload"] | {"mission_day": row["day"]}
            elif row["kind"] == "level3" and row["day"] > d - 7:
                level3.append(row["payload"] | {"astronaut": tags.get(row["member"], row["member"])})
        return {
            "system_keys": list(SYSTEMS), "live": True, "day": d, "crew": list(latest.values()), "level3": level3,
            "packets": outbox.view(self.clock()), "link_up": True, "outbox": str(config.OUTBOX_DIR),
            "delay_minutes": self.store.cfg["sync"]["one_way_delay_minutes"], "flight_seconds": outbox.delay_s,
        }

    def packets(self) -> dict[str, Any]:
        """Only the packet list, so Mission Control can update the countdowns often without rebuilding everything else."""
        queue = self.live.queue
        return {"packets": queue.view(self.clock()), "link_up": queue.link_up or self.mode == "live", "flight_seconds": queue.delay_s}

    def set_link(self, up: bool) -> dict[str, bool]:
        self.live.queue.set_link(up, self.clock())
        return {"link_up": self.live.queue.link_up}

    # Mission clock and demo

    def live_state(self) -> dict[str, Any]:
        return self.live.snapshot(self.clock())

    def set_clock(self, day: int | None = None, running: bool | None = None, days_per_second: float | None = None) -> dict[str, Any]:
        now = self.clock()
        if days_per_second is not None:
            self.live.days_per_second = days_per_second
        if day is not None:
            self.live.set_day(day, now)
        if running is not None:
            self.live.tick(now)
            self.live.running = running
        return self.live.snapshot(now)

    def demo_start(self) -> dict[str, Any]:
        self.live.start_demo(self.clock())
        return self.live_state()

    def demo_next(self) -> dict[str, Any]:
        self.live.next_beat(self.clock())
        return self.live_state()

    def demo_stop(self) -> dict[str, Any]:
        self.live.stop_demo()
        return self.live_state()

    def timeline(self) -> dict[str, Any]:
        """Compact health state for every person and day, so scrubbing needs no recalculation."""
        crew = []
        for who in self.store.crew:
            run = self.store.runs[who.id]
            status = {k: "".join(STATUS_CODE[d["status"]] for d in run.systems[k]) for k in SYSTEMS}
            status["radiation"] = "".join(STATUS_CODE[d["status"]] for d in run.radiation)
            crew.append({
                "id": who.id, "tag": who.tag, "name": who.name, "control": who.control, "status": status,
                "level": [max((a["level"] for a in day), default=0) for day in run.alerts],
            })
        events = [{k: e[k] for k in ("id", "title", "day", "astronaut", "system")} for e in self.store.mission.ground_truth]
        return {"mission_days": self.store.mission.days, "systems": {**SYSTEMS, "radiation": "Radiation"}, "crew": crew, "events": events}

    def _explainer_day(self) -> tuple[int, str, str, float] | None:
        """Find a real day when a flagged person and an unflagged person read the same heart rate."""
        series = self.store.mission.series
        best = None
        for flagged_who in self.store.crew:
            for i, state in enumerate(self.store.runs[flagged_who.id].signals["resting_hr"]):
                if not state.flagged or state.value != state.value:
                    continue
                for other in self.store.crew:
                    peer = self.store.runs[other.id].signals["resting_hr"][i]
                    if other.id == flagged_who.id or peer.flagged or peer.learning or other.control:
                        continue
                    gap = abs(float(series[other.id]["resting_hr"][i]) - state.value)
                    # Prefer an exact match, then the widest gap between the two personal baselines.
                    rank = (gap, -abs(peer.median - state.median))
                    if gap == gap and (best is None or rank < best[0]):
                        best = (rank, i + 1, flagged_who.id, other.id, state.value)
        return best[1:] if best else None

    def explainer(self) -> dict[str, Any]:
        found = self._explainer_day()
        if not found:
            return {"available": False}
        day, flagged, normal, value = found
        people = []
        for who, verdict in ((flagged, "alert"), (normal, "normal")):
            member = self.store.who(who)
            state = self.store.runs[who].signals["resting_hr"][day - 1]
            people.append({
                "id": who, "name": member.name, "role": member.role, "verdict": verdict,
                "value": float(self.store.mission.series[who]["resting_hr"][day - 1]),
                "median": round(state.median, 1), "low": round(state.median - 2 * state.sigma, 1),
                "high": round(state.median + 2 * state.sigma, 1), "drift_days": state.drift_days,
                "chart": series_payload(self.store, who, "resting_hr", day, EXPLAINER_WINDOW),
            })
        return {"available": True, "day": day, "value": value, "people": people}

    def results(self) -> dict[str, Any]:
        path = config.SYNTHETIC_DIR / "results.json"
        return {"available": True, **json.loads(path.read_text())} if path.exists() else {"available": False}

    def about(self) -> dict[str, Any]:
        """Every source Vigil draws on, and how many reference figures are checked."""
        ranges = json.loads((config.DATA_DIR / "real_ranges.json").read_text())
        catalog = json.loads((config.DATA_DIR / "sources.json").read_text())["sources"]
        figures = [v for group in ("signals", "radiation", "communication") for v in ranges[group].values()]
        counts = {k: sum(f["status"] == k for f in figures) for k in ("verified", "partly verified", "team choice", "must_verify")}
        return {
            "sources": [{"id": c["id"], "name": c["title"], "use": c["used_for"], "status": c["status"], "checked": c["checked"],
                         "group": c["group"], "url": c["url"]} for c in catalog],
            "figure_counts": counts, "must_verify_count": counts["must_verify"],
            "mode": self.mode,
            "statement": ("Readings come from what your crew enters and imports on this computer. " if self.mode == "live"
                          else "The demo crew and all their readings are simulated. ")
                         + "A flight surgeon has not reviewed the thresholds, and Vigil does not diagnose anything.",
        }

    # Admin

    def _apply_runtime(self) -> None:
        sync = self.store.cfg["sync"]
        if self.mode == "live":
            self.live.queue.delay_s = sync["one_way_delay_minutes"] * 60
            return
        scale = sync["demo_time_scale"] if sync.get("scale_time", True) else 1
        self.live.queue.delay_s = sync["one_way_delay_minutes"] * 60 / scale
        self.live.queue.bandwidth = sync["bandwidth_kb_s"]
        self.live.days_per_second = float(self.store.cfg["mission"]["days_per_second"])
        self.live.set_day(self.live.day, self.clock())

    def get_config(self) -> dict[str, Any]:
        return {"config": self.store.cfg, "signals": [{"id": s.id, "name": s.name} for s in DRIFT_SIGNALS]}

    def put_config(self, values: dict[str, Any]) -> dict[str, Any]:
        previous = config.load_config()
        updated = config.load_config()
        _merge(updated, values)
        if not set(updated["disabled_signals"]) <= {s.id for s in DRIFT_SIGNALS}:
            raise ValueError("disabled_signals names an unknown signal.")
        config.save_config(updated)
        self._audit("thresholds_changed", "", ", ".join(sorted(values)))
        try:
            self.store.rebuild()
        except Exception as err:
            config.save_config(previous)
            self.store.rebuild()
            raise ValueError(f"Those values do not work: {err}") from err
        self._apply_runtime()
        return {"config": self.store.cfg}

    def reset_config(self) -> dict[str, Any]:
        self.store.restore_defaults()
        self._apply_runtime()
        return {"config": self.store.cfg}

    # What needs this person today

    def notices(self, id: str) -> dict[str, Any]:
        """Short prompts for the home screen: what is due, and who needs the Medical Officer."""
        d = self._day(None)
        out = []
        if self.mode == "live":
            if not self.store.checked_in(id, d):
                out.append({"kind": "checkin", "title": "Check in", "route": "/checkin"})
            series = self.store.mission.series[id]
            if all(np.isnan(series[s.id][d - 1]) for s in mission.LOGGABLE):
                out.append({"kind": "log", "title": "Log readings", "route": "/log"})
            needed = self.store.cfg["baseline"]["learning_days"]
            have = self.store.days_with_readings(id)
            if have < needed:
                out.append({"kind": "learning", "title": f"Baseline: {have} of {needed} days", "route": "/log"})
        role = self.accounts.get(id)["role"] if self.actor_role == "system" else self.actor_role
        if role in ("medical", "commander", "presenter"):
            for card in self.crew_view(d)["crew"]:
                if card["id"] != id and card["max_level"] >= 2:
                    out.append({"kind": "crew", "title": f"{card['name']} has a Level {card['max_level']} alert", "route": "/crew"})
        return {"day": d, "notices": out}

    # Readings people enter (live missions)

    def _for_someone_else(self, id: str) -> bool:
        """The Medical Officer entering results for another person sees none of that person's own values."""
        return self.actor_role not in ("system", "presenter") and self.actor != id

    def log_form(self, id: str) -> dict[str, Any]:
        who = self.store.who(id)
        d = self._day(None)
        series = self.store.mission.series[id]
        hide = self._for_someone_else(id)
        groups: dict[str, list[dict[str, Any]]] = {}
        for sig in mission.LOGGABLE:
            past = np.flatnonzero(~np.isnan(series[sig.id][:d]))
            groups.setdefault(SYSTEMS.get(sig.system, "Radiation"), []).append({
                "id": sig.id, "name": sig.name, "unit": sig.unit, "low": sig.low, "high": sig.high, "decimals": sig.decimals,
                "cadence": sig.cadence, "today": None if hide else _finite(series[sig.id][d - 1]),
                "last": None if hide or not len(past) else _finite(series[sig.id][past[-1]]),
                "last_day": None if hide or not len(past) else int(past[-1]) + 1,
            })
        start = date.fromisoformat(self.store.info["start_date"])
        return {
            "member": _identity(who), "day": d, "date": mission.day_date(start, d).isoformat(),
            "groups": [{"name": k, "signals": v} for k, v in groups.items()],
            "days_with_readings": self.store.days_with_readings(id), "learning_days": self.store.cfg["baseline"]["learning_days"],
            "for_someone_else": hide,
            "crew": [_identity(w) for w in self.store.crew] if self.actor_role in ("medical", "system") else [],
        }

    def log_readings(self, id: str, values: dict[str, Any]) -> dict[str, Any]:
        """Check every value first. Save nothing unless all of them are usable."""
        self.store.who(id)
        d = self._day(None)
        allowed = {s.id for s in mission.LOGGABLE}
        errors, rows = {}, []
        for signal, value in values.items():
            if value is None or str(value).strip() == "":
                continue
            try:
                rows.append((signal, mission.check_value(signal, value, allowed), d))
            except ValueError as err:
                errors[signal] = str(err)
        if errors or not rows:
            return {"saved": 0, "errors": errors or {"_": "Enter at least one reading."}}
        self.store.add_entries(id, rows, "manual", self.actor)
        self._audit("readings_logged", id, f"{len(rows)} readings for day {d}")
        return {"saved": len(rows), "errors": {}, "day": d}

    def entries(self, id: str) -> dict[str, Any]:
        self.store.who(id)
        start = date.fromisoformat(self.store.info["start_date"])
        rows = self.store.entries(id)
        if self._for_someone_else(id):
            rows = [r for r in rows if r["entered_by"] == self.actor]  # only what this Medical Officer entered
        return {"entries": [r | {"date": mission.day_date(start, r["day"]).isoformat()} for r in rows]}

    def delete_entry(self, id: str, entry: int) -> dict[str, Any]:
        if self._for_someone_else(id) and all(r["id"] != int(entry) for r in self.entries(id)["entries"]):
            raise PermissionError("You can only remove readings you entered yourself.")
        self.store.delete_entry(id, int(entry))
        self._audit("reading_deleted", id, f"entry {entry}")
        return {"deleted": entry}

    def import_files(self) -> dict[str, Any]:
        """CSV files waiting in the import folder, for example copied from a USB drive."""
        folder = config.IMPORT_DIR
        folder.mkdir(parents=True, exist_ok=True)
        files = sorted((f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMPORT_TYPES), key=lambda f: f.stat().st_mtime, reverse=True)
        return {"folder": str(folder), "files": [{"name": f.name, "kb": round(f.stat().st_size / 1024, 1)} for f in files]}

    def import_file(self, id: str, file: str) -> dict[str, Any]:
        """Import one CSV. A crew member imports only their own rows. The Medical Officer may import for anyone."""
        path = config.IMPORT_DIR / file
        if Path(file).name != file or path.suffix.lower() not in IMPORT_TYPES or not path.is_file():
            raise LookupError("That file is not in the import folder.")
        self.store.who(id)
        anyone = self.actor_role in ("medical", "system")  # like typed entry, only the Medical Officer enters data for others
        crew = self.store.crew if anyone else tuple(w for w in self.store.crew if w.id == id)
        names = {w.id: w.id for w in crew} | {w.name.lower(): w.id for w in crew} | {w.tag.lower(): w.id for w in crew}
        start = date.fromisoformat(self.store.info["start_date"])
        if path.suffix.lower() in (".xml", ".zip"):
            result = mission.read_apple_health(path, start, self._day(None), id)  # one person's export
        else:
            result = mission.read_import(path, start, self._day(None), names, id)
        by_member: dict[str, list[tuple[str, float, int]]] = {}
        for member, signal, value, day in result.rows:
            by_member.setdefault(member, []).append((signal, value, day))
        for member, rows in by_member.items():
            self.store.add_entries(member, rows, f"import:{file}", self.actor)
        if result.rows:
            done = config.IMPORT_DIR / "imported"
            done.mkdir(exist_ok=True)
            shutil.move(path, done / f"{stamp()}-{file}")  # so the same file cannot be imported twice by mistake
        self._audit("readings_imported", ",".join(sorted(by_member)), f"{len(result.rows)} rows from {file}, {result.skipped_count} skipped")
        return {"imported": len(result.rows), "skipped": result.skipped_count, "reasons": result.skipped, "members": sorted(by_member)}

    # Taking data out

    def export_data(self, id: str) -> dict[str, Any]:
        """Everything Vigil holds about one person, as a CSV they can hand to a flight surgeon."""
        who = self.store.who(id)
        d = self._day(None)
        config.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        path = config.EXPORT_DIR / f"vigil-{mission.safe_name(id)}-{stamp()}.csv"
        series = self.store.mission.series[id]
        with path.open("w", newline="") as f:
            out = csv.writer(f)
            out.writerow(["kind", "day", "item", "value", "unit", "note"])
            for sig in SIGNALS:
                for i in np.flatnonzero(~np.isnan(series[sig.id][:d])):
                    out.writerow(["reading", int(i) + 1, sig.name, round(float(series[sig.id][i]), 3), sig.unit, ""])
            with db.connect(self.store.db_path) as con:
                for row in con.execute("SELECT * FROM checkins WHERE astronaut = ? ORDER BY day", (id,)):
                    for key in ("mood", "sleep_quality", "energy", "stress", "symptoms", "journal_score"):
                        out.writerow(["check-in", row["day"], key.replace("_", " "), row[key], "", ""])
                    if row["journal_text"]:
                        out.writerow(["check-in", row["day"], "journal", "", "", row["journal_text"]])
            for ep in self.store.runs[id].episodes:
                out.writerow(["alert", ep.open_day, SYSTEMS[ep.system], f"Level {ep.level}", "", ep.reason])
        self._audit("data_exported", id)
        return {"path": str(path), "name": who.name}

    def report(self, id: str) -> dict[str, Any]:
        """A one-page health summary. The bridge turns it into a PDF."""
        data = self.astronaut(id)
        d = data["day"]
        e = html.escape
        mode_note = "Readings entered by the crew." if self.mode == "live" else "Simulated data. Demo mission."
        rows = "".join(
            f"<tr><td>{e(s['name'])}</td><td>{'Learning' if s['learning'] else e(s['status'].title())}</td>"
            f"<td>{'' if s['learning'] else s['score']}</td><td>{round(s['confidence'] * 100)}%</td></tr>"
            for s in data["systems"]
        )
        alerts = "".join(f"<li><b>Level {a['level']}, {e(a['system_name'])}.</b> {e(a['message'])} {e(a['level_reason'])}</li>" for a in data["alerts"])
        readings = ""
        for sid in [s.id for s in DRIFT_SIGNALS if s.id in self.store.runs[id].signals]:
            p = series_payload(self.store, id, sid, d)
            if p["current"] is None:
                continue
            normal = "Learning" if p["learning"] or p["median"][-1] is None else f"{p['low'][-1]:.{p['decimals']}f} to {p['high'][-1]:.{p['decimals']}f}"
            readings += f"<tr><td>{e(p['name'])}</td><td>{p['current']:.{p['decimals']}f} {e(p['unit'])}</td><td>{normal}</td><td>{'Yes' if p['flagged_now'] else ''}</td></tr>"
        rad = data["radiation"]
        self._audit("report_made", id)
        return {
            "file": str(config.EXPORT_DIR / f"vigil-report-{mission.safe_name(id)}-{stamp()}.pdf"),
            "html": (
                f"<h1>Vigil health summary</h1><p>{e(data['astronaut']['name'])}, {e(data['astronaut']['role'])}. Mission day {d}. "
                f"Printed {datetime.now():%Y-%m-%d %H:%M}. {mode_note}</p>"
                f"<h2>Systems</h2><table border='1' cellpadding='4'><tr><th>System</th><th>Status</th><th>Drift of 100</th><th>Confidence</th></tr>{rows}</table>"
                f"<h2>Alerts</h2>{'<ul>' + alerts + '</ul>' if alerts else '<p>No active alerts.</p>'}"
                f"<h2>Latest readings against this person's normal</h2><table border='1' cellpadding='4'>"
                f"<tr><th>Reading</th><th>Latest</th><th>Personal normal</th><th>Drifting</th></tr>{readings}</table>"
                f"<h2>Radiation</h2><p>Career dose {rad['career_dose_msv']} mSv of {rad['limit_msv']} mSv.</p>"
                "<p><i>A flight surgeon has not reviewed the thresholds. Vigil does not diagnose anything.</i></p>"
            ),
        }

    # The Commander's tools

    def accounts_admin(self) -> dict[str, Any]:
        roles = [k for k in auth.ROLES if k != "presenter" or self.mode == "demo"]
        return {
            "members": self.accounts.list(include_inactive=True), "roles": [{"id": k, "name": auth.ROLES[k]} for k in roles],
            "auto_lock_minutes": db.get_setting(self.store.db_path, "auto_lock_minutes", DEFAULT_AUTO_LOCK_MINUTES),
            "auto_lock_choices": list(AUTO_LOCK_CHOICES), "mode": self.mode,
            "folders": {"outbox": str(config.OUTBOX_DIR), "import": str(config.IMPORT_DIR), "exports": str(config.EXPORT_DIR),
                        "backups": str(config.BACKUP_DIR)},
        }

    def add_member(self, name: str, role: str, pin: str, prior_dose: float = 0.0) -> dict[str, Any]:
        if self.mode == "demo":
            raise ValueError("The demo crew is fixed. Set up a real mission to add people.")
        if role == "presenter":
            raise ValueError("A live mission has no presenter account.")
        member = self.accounts.create(name, role, str(pin), float(prior_dose), must_change=True)
        self._audit("member_added", member["id"], member["role_name"])
        self.store.rebuild()
        return {"member": member}

    def update_member(self, member: str, name: str | None = None, role: str | None = None,
                      prior_dose: float | None = None, active: bool | None = None) -> dict[str, Any]:
        if self.mode == "demo" and member in DEMO_ROLES and (role is not None or active is False):
            raise ValueError("The demo crew keep their roles. Set up a mission to manage a real crew.")
        updated = self.accounts.update(member, name, role, prior_dose, active)
        changed = ", ".join(k for k, v in (("name", name), ("role", role), ("prior dose", prior_dose), ("active", active)) if v is not None)
        self._audit("member_changed", member, changed)
        self.store.rebuild()
        return {"member": updated}

    def reset_member_pin(self, member: str, pin: str) -> dict[str, Any]:
        self.accounts.set_pin(member, str(pin), must_change=True)
        self._audit("pin_reset", member)
        return {"member": self.accounts.get(member)}

    def unlock_member(self, member: str) -> dict[str, Any]:
        self.accounts.unlock(member)
        self._audit("member_unlocked", member)
        return {"member": self.accounts.get(member)}

    def set_auto_lock(self, minutes: int) -> dict[str, Any]:
        if minutes not in AUTO_LOCK_CHOICES:
            raise ValueError(f"Choose one of {', '.join(map(str, AUTO_LOCK_CHOICES))} minutes.")
        db.set_setting(self.store.db_path, "auto_lock_minutes", minutes)
        self._audit("auto_lock_changed", "", f"{minutes} minutes")
        return {"auto_lock_minutes": minutes}

    def audit_log(self, limit: int = AUDIT_LIMIT) -> dict[str, Any]:
        names = {m["id"]: m["name"] for m in self.accounts.list(include_inactive=True)}
        rows = db.audit_log(self.store.db_path, min(int(limit), AUDIT_LIMIT))
        return {"events": [r | {"when": datetime.fromtimestamp(r["at"]).strftime("%Y-%m-%d %H:%M:%S"),
                                "who": names.get(r["actor"], r["actor"]), "about": names.get(r["target"], r["target"])} for r in rows]}

    def backup(self) -> dict[str, Any]:
        path = db.backup(self.store.db_path, config.BACKUP_DIR, stamp())
        self._audit("backup_made", "", path.name)
        return {"path": str(path)}
