"""What each audience may see. Raw values and journal text stay with the astronaut by default."""

from typing import Any

from ..engine.pipeline import AstronautRun
from ..signals import SYSTEMS

TREND_DAYS = 30


def _latest_values(run: AstronautRun, day: int) -> dict[str, Any]:
    """Raw last readings. Only used after the astronaut turns on sharing."""
    return {
        sid: None if states[day - 1].last_value != states[day - 1].last_value else states[day - 1].last_value
        for sid, states in run.signals.items()
    }


def _identity(run: AstronautRun) -> dict[str, Any]:
    w = run.who
    return {"id": w.id, "name": w.name, "role": w.role, "tag": w.tag, "control": w.control}


def crew_card(run: AstronautRun, day: int, alerts: list[dict], share: bool) -> dict[str, Any]:
    """Crew tier: trends and status only."""
    systems = [
        {
            "id": key, "name": name, "status": run.systems[key][day - 1]["status"],
            "learning": run.systems[key][day - 1]["learning"],
            "trend": [d["score"] for d in run.systems[key][max(0, day - TREND_DAYS): day]],
        }
        for key, name in SYSTEMS.items()
    ]
    card = {**_identity(run), "systems": systems, "max_level": max((a["level"] for a in alerts), default=0)}
    return card | ({"shared_values": _latest_values(run, day)} if share else {})


def ground_card(run: AstronautRun, day: int, alerts: list[dict], share: bool) -> dict[str, Any]:
    """Ground tier: a summary, plus any Level 3 alert without numbers."""
    level3 = [
        {"id": a["id"], "system": a["system_name"], "level": 3, "opened_day": a["opened_day"], "reason": a["level_reason"]}
        for a in alerts if a["level"] >= 3
    ]
    summary = {
        **_identity(run),
        # "none" means no baseline yet, so Earth never reads "Normal" for a system Vigil cannot judge.
        "systems": {k: "none" if run.systems[k][day - 1]["learning"] else run.systems[k][day - 1]["status"] for k in SYSTEMS},
        "radiation": run.radiation[day - 1]["status"],
        "max_level": max((a["level"] for a in alerts), default=0),
        "level3": level3,
    }
    return summary | ({"shared_values": _latest_values(run, day)} if share else {})
