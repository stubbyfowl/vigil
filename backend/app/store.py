"""The finished mission in memory, plus what the astronaut has done to it."""

import shutil
from typing import Any

from fastapi import HTTPException

from . import config, db
from .engine.checkin import score_text
from .engine.pipeline import AstronautRun, run_astronaut, run_mission
from .models import CheckIn
from .signals import BY_ID
from .sim.generator import CREW, Astronaut, Mission, generate_mission

HIDE_NOTHING: dict[str, Any] = {}


class Store:
    def __init__(self) -> None:
        self.version = 0
        self.actions: dict[str, dict[str, int]] = {}
        self.cfg: config.Config = {}
        self.mission: Mission
        self.runs: dict[str, AstronautRun] = {}
        self.rebuild()

    def rebuild(self) -> None:
        """Regenerate from the seed, reapply check-ins, and run the engine."""
        self.cfg = config.load_config()
        m = self.cfg["mission"]
        self.mission = generate_mission(m["seed"], m["length_days"])
        with db.connect() as con:
            rows = con.execute("SELECT * FROM checkins").fetchall()
            self.actions = {}
            for row in con.execute("SELECT * FROM alert_actions"):
                self._remember_action(row["alert_id"], row["action"], row["day"], row["level"])
        for row in rows:
            self._write_checkin_values(row["astronaut"], row["day"], dict(row))
        self.runs = run_mission(self.mission, self.cfg)
        self.version += 1

    def reset_interactive(self) -> None:
        """Forget check-ins, alert actions and share choices. Used before each demo."""
        with db.connect() as con:
            for table in ("checkins", "alert_actions", "share_prefs"):
                con.execute(f"DELETE FROM {table}")
        self.rebuild()

    def restore_defaults(self) -> None:
        shutil.copy(config.THRESHOLDS_PATH.with_name("thresholds.defaults.yaml"), config.THRESHOLDS_PATH)
        self.rebuild()

    def who(self, astronaut: str) -> Astronaut:
        for member in CREW:
            if member.id == astronaut:
                return member
        raise HTTPException(404, f"No crew member named {astronaut}.")

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
        with db.connect() as con:
            con.execute("INSERT INTO alert_actions VALUES (?,?,?,?)", (alert_id, day, action, level))
        self._remember_action(alert_id, action, day, level)

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
        row = body.model_dump() | {"journal_score": journal_score}
        with db.connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO checkins VALUES (?,?,?,?,?,?,?,?,?)",
                (body.astronaut, day, body.mood, body.sleep_quality, body.energy, body.stress, body.symptoms,
                 journal_score, body.journal if body.keep_text else None),
            )
        self._write_checkin_values(body.astronaut, day, row)
        self.runs[body.astronaut] = run_astronaut(self.who(body.astronaut), self.mission, self.cfg)
        self.version += 1
        return journal_score

    # Sharing

    def share(self, astronaut: str) -> dict[str, bool]:
        with db.connect() as con:
            row = con.execute("SELECT * FROM share_prefs WHERE astronaut = ?", (astronaut,)).fetchone()
        return {"share_crew": bool(row and row["share_crew"]), "share_ground": bool(row and row["share_ground"])}

    def set_share(self, astronaut: str, crew: bool | None, ground: bool | None) -> dict[str, bool]:
        now = self.share(astronaut)
        merged = (astronaut, int(now["share_crew"] if crew is None else crew), int(now["share_ground"] if ground is None else ground))
        with db.connect() as con:
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
