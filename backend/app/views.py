"""Everything the screens read and do. One process, no server, no open ports."""

import json
import re
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from . import config
from .engine.alerts import PROTOCOLS
from .live import Live
from .models import CheckIn
from .signals import DRIFT_SIGNALS, SIGNALS, SYSTEMS
from .sim.generator import CREW
from .store import Store, series_payload
from .sync.privacy import crew_card, ground_card
from .sync.queue import PRIORITY_LEVEL3, PRIORITY_NORMAL

TREND_DAYS = 30
CHART_SIGNALS = 3
EXPLAINER_WINDOW = 50
CALL_PACKET_KB = 32.0
STATUS_CODE = {"green": "g", "yellow": "y", "red": "r"}
EARTH_DECISIONS = {
    0: ("none", "No need to call Earth.", "All systems are inside your normal. A routine summary goes out each week."),
    1: ("self", "Handle this on board.", "A small change. Follow the self-care step and recheck. Earth does not need to wait on this."),
    2: ("crew", "Tell the Medical Officer.", "The change is wider or longer. The crew can run a longer check before Earth could answer."),
    3: ("earth", "Send a priority packet now.", "A Level 3 condition is active. Act on the checklist while the packet travels."),
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

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.store = Store()
        self.live = Live(self.store, clock())

    def _day(self, day: int | None) -> int:
        return self.store.clamp_day(day) if day is not None else self.live.snapshot(self.clock())["day"]

    # The astronaut's own screens

    def crew(self) -> dict[str, Any]:
        return {
            "crew": [_identity(w) for w in CREW], "systems": SYSTEMS,
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

    def undo_alert_action(self, alert_id: str) -> dict[str, Any]:
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
        top = next((a for a in alerts if a["level"] == level), None)
        return {
            "level": level, "decision": kind, "title": title, "detail": detail, "reason": top["level_reason"] if top else None,
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
        cards = [crew_card(store.runs[w.id], d, store.alerts(w.id, d), store.share(w.id)["share_crew"]) for w in CREW if not w.control]
        watching = sum(c["max_level"] > 0 or any(s["status"] != "green" for s in c["systems"]) for c in cards)
        summary = "All crew inside their normal." if not watching else f"{watching} of {len(cards)} crew need attention."
        return {"day": d, "crew": cards, "summary": summary}

    def ground(self, day: int | None = None) -> dict[str, Any]:
        d = self._day(day)
        store = self.store
        cards = [ground_card(store.runs[w.id], d, store.alerts(w.id, d, include_hidden=True), store.share(w.id)["share_ground"]) for w in CREW]
        return {
            "day": d, "crew": cards, "level3": [a | {"astronaut": c["tag"]} for c in cards for a in c["level3"]],
            "packets": self.live.queue.view(self.clock()), "link_up": self.live.queue.link_up,
            "delay_minutes": store.cfg["sync"]["one_way_delay_minutes"], "flight_seconds": self.live.queue.delay_s,
        }

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
        for who in CREW:
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
        for flagged_who in CREW:
            for i, state in enumerate(self.store.runs[flagged_who.id].signals["resting_hr"]):
                if not state.flagged or state.value != state.value:
                    continue
                for other in CREW:
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
        ranges = json.loads((config.DATA_DIR / "real_ranges.json").read_text())
        table = (config.ROOT / "SOURCES.md").read_text().split("## Numbers")[0]
        rows = re.findall(r"^\| (?!Source|---)(.+?) \| (.+?) \| (.+?) \|$", table, flags=re.M)
        groups = ("signals", "radiation", "communication")
        return {
            "sources": [{"name": n, "use": u, "status": s} for n, u, s in rows],
            "must_verify_count": sum(v["status"] == "must_verify" for g in groups for v in ranges[g].values()),
            "statement": "All crew data in Vigil is synthetic. Thresholds are starting values, not clinical limits. "
                         "Vigil gives decision support, not a diagnosis.",
        }

    # Admin

    def _apply_runtime(self) -> None:
        sync = self.store.cfg["sync"]
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
