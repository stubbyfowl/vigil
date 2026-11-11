"""The mission in memory, plus what the crew has done to it.

A demo mission is generated from a seed. A live mission is built from what people entered.
"""

import json
import shutil
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from . import auth, config, db, mission
from .engine.checkin import score_text
from .engine.pipeline import AstronautRun, run_astronaut, run_mission
from .models import CheckIn
from .signals import BY_ID
from .sim.generator import CREW, Astronaut, Mission, generate_mission

HIDE_NOTHING: dict[str, Any] = {}
RECENT_ENTRIES = 40


class Store:
    def __init__(self, mode: str = "demo", path: Path | None = None, today: Callable[[], date] = date.today) -> None:
        self.mode = mode
        self.db_path = path or config.DB_PATH
        self.today = today
        self.version = 0
        self.actions: dict[str, dict[str, int]] = {}
        self.cfg: config.Config = {}
        self.info: dict[str, Any] = {}
        self.crew: tuple[Astronaut, ...] = CREW
        self.mission: Mission
        self.runs: dict[str, AstronautRun] = {}
        self.rebuild()

    # Which day it is, and who is aboard

    def current_day(self) -> int:
        """Live missions follow the calendar. Day 1 is the start date."""
        start = date.fromisoformat(self.info["start_date"])
        return max(1, min(mission.mission_day(start, self.today()), self.info["length_days"]))

    def _live_crew(self) -> tuple[Astronaut, ...]:
        with db.connect(self.db_path) as con:
            rows = con.execute("SELECT * FROM members WHERE active = 1 ORDER BY created_at").fetchall()
        return tuple(
            Astronaut(r["id"], r["name"], auth.ROLES[r["role"]], r["tag"], float(r["prior_dose"]))
            for r in rows if r["role"] in auth.CREW_ROLES
        )

    def rebuild(self) -> None:
        """Rebuild the mission, reapply check-ins, and run the engine."""
        self.cfg = config.load_config()
        if self.mode == "live":
            with db.connect(self.db_path) as con:
                self.info = {r["key"]: json.loads(r["value"]) for r in con.execute("SELECT * FROM settings")}
            self.crew = self._live_crew()
            with db.connect(self.db_path) as con:
                self.mission = mission.build(con, self.crew, self.current_day())
        else:
            m = self.cfg["mission"]
            self.crew = CREW
            self.mission = generate_mission(m["seed"], m["length_days"])
        with db.connect(self.db_path) as con:
            rows = con.execute("SELECT * FROM checkins").fetchall()
            self.actions = {}
            for row in con.execute("SELECT * FROM alert_actions"):
                self._remember_action(row["alert_id"], row["action"], row["day"], row["level"])
        known = {w.id for w in self.crew}
        for row in rows:
            if row["astronaut"] in known and row["day"] <= self.mission.days:
                self._write_checkin_values(row["astronaut"], row["day"], dict(row))
        self.runs = run_mission(self.mission, self.cfg, crew=self.crew)
        self.version += 1

    def reset_interactive(self) -> None:
        """Forget check-ins, alert actions and share choices. Used before each demo."""
        with db.connect(self.db_path) as con:
            for table in ("checkins", "alert_actions", "share_prefs"):
                con.execute(f"DELETE FROM {table}")
        self.rebuild()

    def restore_defaults(self) -> None:
        shutil.copy(config.DEFAULTS_PATH, config.THRESHOLDS_PATH)
        self.rebuild()

    def who(self, astronaut: str) -> Astronaut:
        for member in self.crew:
            if member.id == astronaut:
                return member
        raise LookupError(f"No crew member named {astronaut}.")

    def clamp_day(self, day: int) -> int:
        return max(1, min(day, self.mission.days))

    # Alerts as the astronaut sees them

    def _remember_action(self, alert_id: str, action: str, day: int, level: int) -> None:
        state = self.actions.setdefault(alert_id, {})
        if action == "done":
            state["done_level"] = level
        elif action == "snooze":
            state["snooze_day"] = day  # data arrives daily, so 2 hours lasts until the next day
        elif action == "escalate":
            state["level"] = min(max(level + 1, state.get("level", 0)), 3)

    def _apply_action(self, alert: dict[str, Any]) -> dict[str, Any]:
        state = self.actions.get(alert["id"], HIDE_NOTHING)
        forced = state.get("level", 0)
        if forced > alert["level"]:
            reason = f"Escalated to Level {forced} by the astronaut."
            return {**alert, "level": forced, "level_reason": reason, "why": {**alert["why"], "rule": reason}}
        return alert

    def alerts(self, astronaut: str, day: int, include_hidden: bool = False) -> list[dict[str, Any]]:
        """Active alerts today, with astronaut actions applied."""
        out = []
        for raw in self.runs[astronaut].alerts[day - 1]:
            alert = self._apply_action(raw)
            state = self.actions.get(alert["id"], HIDE_NOTHING)
            hidden = alert["level"] <= state.get("done_level", 0) or state.get("snooze_day") == day
            if include_hidden or not hidden:
                out.append(alert)
        return out

    def record_action(self, alert_id: str, action: str, day: int, level: int) -> None:
        with db.connect(self.db_path) as con:
            con.execute("INSERT INTO alert_actions VALUES (?,?,?,?)", (alert_id, day, action, level))
        self._remember_action(alert_id, action, day, level)

    def undo_action(self, alert_id: str) -> None:
        """Take back the most recent action on this alert."""
        with db.connect(self.db_path) as con:
            con.execute("DELETE FROM alert_actions WHERE rowid = (SELECT MAX(rowid) FROM alert_actions WHERE alert_id = ?)", (alert_id,))
            rows = con.execute("SELECT * FROM alert_actions WHERE alert_id = ? ORDER BY rowid", (alert_id,)).fetchall()
        self.actions.pop(alert_id, None)
        for row in rows:
            self._remember_action(alert_id, row["action"], row["day"], row["level"])

    # Check-ins

    def _write_checkin_values(self, astronaut: str, day: int, row: dict[str, Any]) -> None:
        series = self.mission.series[astronaut]
        for signal in ("mood", "energy", "stress", "symptoms"):
            series[signal][day - 1] = float(row[signal])
        series["journal"][day - 1] = float(row["journal_score"])

    def save_checkin(self, body: CheckIn, day: int) -> float:
        """Store scores, and the text only if the astronaut asked. Then rerun that person."""
        self.who(body.astronaut)
        journal_score = score_text(body.journal)
        row = asdict(body) | {"journal_score": journal_score}
        with db.connect(self.db_path) as con:
            con.execute(
                "INSERT OR REPLACE INTO checkins VALUES (?,?,?,?,?,?,?,?,?)",
                (body.astronaut, day, body.mood, body.sleep_quality, body.energy, body.stress, body.symptoms,
                 journal_score, body.journal if body.keep_text else None),
            )
        self._write_checkin_values(body.astronaut, day, row)
        self.runs[body.astronaut] = run_astronaut(self.who(body.astronaut), self.mission, self.cfg)
        self.version += 1
        return journal_score

    def checked_in(self, astronaut: str, day: int) -> bool:
        with db.connect(self.db_path) as con:
            return con.execute("SELECT 1 FROM checkins WHERE astronaut = ? AND day = ?", (astronaut, day)).fetchone() is not None

    # Readings people enter or import (live missions)

    def add_entries(self, member: str, rows: list[tuple[str, float, int]], source: str, entered_by: str) -> int:
        """Store readings that were already checked, then rerun the engine."""
        self.who(member)
        now = time.time()
        with db.connect(self.db_path) as con:
            con.executemany(
                "INSERT INTO entries (member, signal, value, day, source, entered_by, created_at) VALUES (?,?,?,?,?,?,?)",
                [(member, signal, value, day, source, entered_by, now) for signal, value, day in rows],
            )
        self.rebuild()
        return len(rows)

    def delete_entry(self, member: str, entry_id: int) -> None:
        with db.connect(self.db_path) as con:
            gone = con.execute("DELETE FROM entries WHERE id = ? AND member = ?", (entry_id, member)).rowcount
        if not gone:
            raise LookupError("That reading is already gone.")
        self.rebuild()

    def entries(self, member: str, limit: int = RECENT_ENTRIES) -> list[dict[str, Any]]:
        with db.connect(self.db_path) as con:
            rows = con.execute("SELECT * FROM entries WHERE member = ? ORDER BY day DESC, id DESC LIMIT ?", (member, limit)).fetchall()
        return [dict(r) | {"name": BY_ID[r["signal"]].name, "unit": BY_ID[r["signal"]].unit} for r in rows]

    def days_with_readings(self, member: str) -> int:
        with db.connect(self.db_path) as con:
            return con.execute("SELECT COUNT(DISTINCT day) FROM entries WHERE member = ?", (member,)).fetchone()[0]

    # Sharing

    def share(self, astronaut: str) -> dict[str, bool]:
        with db.connect(self.db_path) as con:
            row = con.execute("SELECT * FROM share_prefs WHERE astronaut = ?", (astronaut,)).fetchone()
        return {"share_crew": bool(row and row["share_crew"]), "share_ground": bool(row and row["share_ground"])}

    def set_share(self, astronaut: str, crew: bool | None, ground: bool | None) -> dict[str, bool]:
        now = self.share(astronaut)
        merged = (astronaut, int(now["share_crew"] if crew is None else crew), int(now["share_ground"] if ground is None else ground))
        with db.connect(self.db_path) as con:
            con.execute("INSERT OR REPLACE INTO share_prefs (astronaut, share_crew, share_ground) VALUES (?,?,?)", merged)
        return self.share(astronaut)


def series_payload(store: Store, astronaut: str, signal: str, day: int, window: int | None = None) -> dict[str, Any]:
    """Chart data for one signal, up to and including the given day."""
    states = store.runs[astronaut].signals[signal][:day]
    first = max(0, day - window) if window else 0
    picked = states[first:]
    sig = BY_ID[signal]
    clean = lambda v: None if v != v else round(v, 3)  # noqa: E731
    last = states[-1]
    return {
        "id": sig.id, "name": sig.name, "unit": sig.unit, "bad": sig.bad, "cadence": sig.cadence, "decimals": sig.decimals,
        "days": list(range(first + 1, day + 1)),
        "values": [clean(s.value) for s in picked],
        "low": [None if s.learning else clean(s.median - 2 * s.sigma) for s in picked],
        "high": [None if s.learning else clean(s.median + 2 * s.sigma) for s in picked],
        "median": [None if s.learning else clean(s.median) for s in picked],
        "flagged": [s.flagged for s in picked],
        "current": clean(last.last_value), "learning": last.learning, "flagged_now": last.flagged,
        "drift_days": last.drift_days,
        "recent_median": clean(last.short_median),
    }
