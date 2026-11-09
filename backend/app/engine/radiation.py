"""Track dose against the limit, project the mission total, and handle storms."""

from typing import Any

import numpy as np

from ..config import Config
from ..sim.generator import Astronaut, Mission
from .alerts import DISCLAIMER

HOURS = 24
PROJECTION_DAYS = 30


def _dose_rate_for_projection(cum: np.ndarray, day: int, storm_days: set[int]) -> float:
    """Recent average daily dose, leaving out storm days."""
    daily = np.diff(cum[: day], prepend=0.0)
    recent = [v for i, v in enumerate(daily, start=1) if i > day - PROJECTION_DAYS and i not in storm_days]
    return float(np.mean(recent)) if recent else 0.0


def storm_phase(mission: Mission, day: int) -> str:
    """Return none, active or passed for the given mission day."""
    if not mission.storm:
        return "none"
    first = mission.storm["onset_hour"] // HOURS + 1
    last = (mission.storm["end_hour"] - 1) // HOURS + 1
    return "active" if first <= day <= last else "passed" if day > last else "none"


def _storm_summary(mission: Mission, who: Astronaut, day: int) -> dict[str, Any]:
    phase = storm_phase(mission, day)
    summary: dict[str, Any] = {"phase": phase}
    if phase == "none" or not mission.storm:
        return summary
    s = mission.storm
    limit_hour = min(day * HOURS, s["end_hour"])
    received = float(mission.hourly[who.id][s["onset_hour"]:limit_hour].sum() / 1000)
    free = float(mission.hourly_free[who.id][s["onset_hour"]:limit_hour].sum() / 1000)
    start = max(s["warning_hour"] - 6, 0)
    summary.update(
        warning_hour=s["warning_hour"] - start, onset_hour=s["onset_hour"] - start, end_hour=s["end_hour"] - start,
        hourly=[round(float(v)) for v in mission.hourly[who.id][start:s["end_hour"] + 6]],
        hourly_free=[round(float(v)) for v in mission.hourly_free[who.id][start:s["end_hour"] + 6]],
        shelter_dose_msv=round(received, 2), unsheltered_dose_msv=round(free, 2),
    )
    return summary


def radiation_day(mission: Mission, who: Astronaut, day: int, cfg: Config) -> dict[str, Any]:
    """Radiation state for one person on one mission day."""
    r = cfg["radiation"]
    limit = r["career_limit_msv"]
    series = mission.series[who.id]
    cum = series["cum_dose"]
    mission_dose = float(cum[day - 1])
    career = who.prior_dose + mission_dose
    storm_days = {120, 121} if mission.storm else set()
    daily_rate = _dose_rate_for_projection(cum, day, storm_days)
    projected = career + daily_rate * (mission.days - day)
    fraction = career / limit
    storm = _storm_summary(mission, who, day)
    active = storm["phase"] == "active"
    peak_rate = float(mission.hourly_free[who.id][(day - 1) * HOURS: day * HOURS].max())
    score = max(100 * fraction, min(100.0, 75 * peak_rate / r["dose_rate_warn_usv_h"]))
    near = fraction >= r["near_limit_fraction"]
    status = "red" if active or near else "yellow" if fraction >= r["watch_fraction"] else "green"
    return {
        "score": round(score), "status": status, "fraction": round(fraction, 3),
        "career_dose_msv": round(career, 1), "prior_dose_msv": who.prior_dose,
        "mission_dose_msv": round(mission_dose, 1), "today_dose_msv": round(float(series["daily_dose"][day - 1]), 2),
        "dose_rate_usv_h": round(float(series["dose_rate"][day - 1]), 1), "peak_rate_usv_h": round(peak_rate),
        "projected_total_msv": round(projected, 1), "limit_msv": limit,
        "near_limit": near, "storm": storm,
    }


def _alert(who: Astronaut, open_day: int, today: int, message: str, action: str, reason: str, why: list) -> dict:
    return {
        "id": f"{who.id}-radiation-{open_day}", "astronaut": who.id, "system": "radiation", "system_name": "Radiation",
        "opened_day": open_day, "day": today, "level": 3, "level_reason": reason, "message": message, "action": action,
        "protocol": "shelter", "recheck_hours": 1, "recheck_text": "Recheck in 1 hour.",
        "disclaimer": DISCLAIMER, "score": 100, "why": {"signals": why, "rule": reason}, "top_signal": "dose_rate",
    }


def radiation_alert(mission: Mission, who: Astronaut, day: int, state: dict[str, Any], cfg: Config) -> dict | None:
    """Return a Level 3 alert during a storm, or when dose nears the limit."""
    limit = cfg["radiation"]["career_limit_msv"]
    base = float(np.nanmedian(mission.series[who.id]["dose_rate"][: max(day - 1, 1)]))
    row = {
        "signal": "dose_rate", "name": "Dose rate", "unit": "uSv/h", "baseline_median": round(base, 1),
        "baseline_low": round(base * 0.9, 1), "baseline_high": round(base * 1.1, 1),
        "current": state["peak_rate_usv_h"], "change": round(state["peak_rate_usv_h"] - base, 1),
        "days_of_drift": 1, "rule": "The solar monitor raised a storm flag, or dose rate crossed the warning level.",
    }
    if state["storm"]["phase"] == "active" and mission.storm:
        return _alert(
            who, mission.storm["onset_hour"] // HOURS + 1, day,
            f"Solar storm. Dose rate reached {state['peak_rate_usv_h']} uSv per hour outside the shelter. "
            "A warning came 2 hours before the spike. Radiation can harm the blood and raise long-term cancer risk.",
            "Go to the storm shelter now and follow the checklist.",
            "Escalated to Level 3 because a solar storm crossed the dose rate warning level.", [row],
        )
    if state["near_limit"]:
        return _alert(
            who, day, day,
            f"Your dose is {state['career_dose_msv']} mSv. That is {state['fraction'] * 100:.0f}% of the {limit} mSv limit. "
            "More dose brings you closer to the limit.",
            "Send the priority packet to Earth and review your dose plan.",
            "Escalated to Level 3 because radiation is near a limit.", [row],
        )
    return None
