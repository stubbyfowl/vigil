"""The body map: every reading placed on the body, tied to NASA's five hazards of human spaceflight and its named risks.

Hazards and risk names come from NASA's Human Research Program (sources hrp_hazards and hrp_risks). Blood sugar
ranges come from the CDC (cdc_glucose, cdc_low_sugar) and the cabin CO2 limit from NASA-STD-3001 (nasa_std_3001_co2).
"""

import json
from typing import Any

import numpy as np

from . import config
from .engine.pipeline import AstronautRun
from .signals import BY_ID, DRIFT_SIGNALS

# NASA's five hazards, in its words where they are short enough, and what Vigil watches for each.
HAZARDS: list[dict[str, str]] = [
    {"id": "radiation", "name": "Space radiation", "nasa": "Invisible to the human eye, and one of the most dangerous parts of spaceflight.",
     "vigil": "Daily dose against NASA's career and per-storm limits, with real solar storms from NOAA and NASA DONKI."},
    {"id": "isolation", "name": "Isolation and confinement", "nasa": "Small crews confined for months can show behavioral changes, so crews must be chosen, trained and supported.",
     "vigil": "Mood, stress, energy, sleep, social time and journal tone, each against the person's own normal."},
    {"id": "distance", "name": "Distance from Earth", "nasa": "Mars is on average 140 million miles away. Supplies, instructions and medical care get harder to reach.",
     "vigil": "Decides on board when to handle something, tell the Medical Officer, or call Earth with a 22-minute delay."},
    {"id": "gravity", "name": "Gravity fields", "nasa": "Muscles, bones, the inner ear and organs must adjust to each change in gravity, such as three-eighths of Earth's on Mars.",
     "vigil": "Bone marker, grip, exercise, lean mass, blood pressure and the heart rate rise on standing."},
    {"id": "closed", "name": "Hostile closed environments", "nasa": "A spacecraft's temperature, pressure, lighting, noise and microbes must all be managed.",
     "vigil": "Cabin CO2 against NASA's limit, blood oxygen, and immune signs of infection."},
]

REGIONS: list[dict[str, Any]] = [
    {"id": "brain", "name": "Brain and sleep", "system": "behavior", "x": 0.5, "y": 0.07,
     "function": "Runs mood, focus, decisions and sleep. Isolation and broken sleep show here first.",
     "hazards": ["isolation", "distance", "radiation"],
     "risks": ["Risk of Behavioral Changes and Psychiatric Disorders", "Risk of Inadequate Sleep and Irregular Schedules", "Risk of Altered Sensorimotor and Vestibular Function"],
     "signals": ["mood", "stress", "energy", "sleep_hours", "sleep_eff", "social_min"],
     "links": [["/system/behavior", "Behavior readings"], ["/chat/future", "Texts from you at 70"]]},
    {"id": "lungs", "name": "Lungs and air", "system": None, "x": 0.4, "y": 0.29,
     "function": "Brings oxygen in and carbon dioxide out. In a sealed cabin, the air itself has to be watched.",
     "hazards": ["closed"],
     "risks": ["Risk of Hypoxia"],
     "signals": ["spo2", "co2"],
     "links": [["/system/heart", "Heart readings"]]},
    {"id": "heart", "name": "Heart and vessels", "system": "heart", "x": 0.56, "y": 0.32,
     "function": "Pumps blood against gravity on Earth. In space it adapts, and standing up again can be hard.",
     "hazards": ["gravity", "radiation"],
     "risks": ["Risk of Cardiovascular Adaptations", "Risk of Reduced Cardiorespiratory and Musculoskeletal Fitness"],
     "signals": ["resting_hr", "hrv", "bp_sys", "bp_dia", "ortho_rise"],
     "links": [["/system/heart", "Heart readings"], ["/album", "Heart rate album"]]},
    {"id": "immune", "name": "Immune system", "system": "immune", "x": 0.62, "y": 0.2,
     "function": "Fights infection. Stress, radiation and the closed cabin can all change how it responds.",
     "hazards": ["closed", "radiation", "isolation"],
     "risks": ["Risk of Altered Immune System Responses", "Risk of Host-Microorganism Interactions"],
     "signals": ["temp", "crp", "il6", "lymph", "symptoms"],
     "links": [["/system/immune", "Immune readings"], ["/replay", "Immune replay"]]},
    {"id": "gut", "name": "Gut and nutrition", "system": None, "x": 0.5, "y": 0.45,
     "function": "Turns stored food into energy. What you eat and how your blood sugar holds up show how well you are fuelled.",
     "hazards": ["distance", "closed"],
     "risks": ["Risk of Inadequate Food and Nutrition"],
     "signals": ["glucose", "body_mass", "fiber", "processed"],
     "links": [["/gut", "Gut City"], ["/checkin", "Check in"]]},
    {"id": "bones", "name": "Bones and muscles", "system": "bone", "x": 0.43, "y": 0.72,
     "function": "Hold you up and move you. Without gravity they weaken unless they are loaded every day.",
     "hazards": ["gravity"],
     "risks": ["Risk of Spaceflight-Induced Bone Changes", "Risk of Reduced Cardiorespiratory and Musculoskeletal Fitness"],
     "signals": ["exercise_min", "grip", "bone_marker", "lean_mass"],
     "links": [["/system/bone", "Bone and muscle readings"]]},
    {"id": "radiation", "name": "Radiation dose", "system": None, "x": 0.66, "y": 0.6,
     "function": "Radiation passes through the whole body. Your personal dosimeter adds it up day by day.",
     "hazards": ["radiation"],
     "risks": ["Risk of Radiation-Induced Cancers"],
     "signals": ["daily_dose"],
     "links": [["/radiation", "Radiation"]]},
]

REFERENCE = {"glucose", "body_mass", "co2"}  # judged against published ranges, not a personal baseline
RANK = {"none": 0, "green": 1, "yellow": 2, "red": 3}


def guide() -> dict[str, dict[str, str]]:
    return json.loads((config.DATA_DIR / "indicator_guide.json").read_text())


def reference_status(sid: str, value: float, first: float | None) -> tuple[str, str, str]:
    """Status, word and range text for readings with a published range."""
    if sid == "glucose":
        # CDC: fasting 99 or below is normal, 100 to 125 prediabetes, 126 or above diabetes; below 70 is low, below 54 severe.
        if value < 54:
            return "red", "Severe low", "70 to 99 fasting"
        if value < 70:
            return "red", "Low", "70 to 99 fasting"
        if value <= 99:
            return "green", "Normal", "70 to 99 fasting"
        if value <= 125:
            return "yellow", "Above normal", "70 to 99 fasting"
        return "red", "High", "70 to 99 fasting"
    if sid == "co2":
        # NASA-STD-3001: cabin CO2 held to a one-hour average of 3 mmHg [V2 6004].
        return ("green", "Within NASA's limit", "NASA limit 3") if value <= 3.0 else ("red", "Above NASA's limit", "NASA limit 3")
    change = value - first if first is not None else 0.0
    return "none", f"{change:+.1f} kg since first", "your first reading"


def _latest(series: np.ndarray, day: int) -> tuple[float | None, int | None, float | None]:
    known = np.flatnonzero(~np.isnan(series[:day]))
    if not len(known):
        return None, None, None
    return float(series[known[-1]]), int(known[-1]) + 1, float(series[known[0]])


def _row(run: AstronautRun, series: dict[str, np.ndarray], sid: str, day: int, notes: dict[str, dict[str, str]]) -> dict[str, Any]:
    sig = BY_ID[sid]
    value, on_day, first = _latest(series[sid], day)
    row: dict[str, Any] = {"id": sid, "name": sig.name, "unit": sig.unit, "value": None, "day": on_day, "status": "none",
                           "word": "No reading yet", "range": "", "guide": notes.get(sid, {})}
    if value is None:
        return row
    row["value"] = round(value, sig.decimals)
    if sid in REFERENCE:
        row["status"], row["word"], row["range"] = reference_status(sid, value, first)
    elif sid in ("fiber", "processed"):
        row["word"], row["range"] = "Reported in the check-in", "servings, 0 to 5"
    elif sid == "daily_dose":
        row["word"], row["range"] = "From your dosimeter", "mSv in a day"
    elif sid in run.signals:
        state = run.signals[sid][day - 1]
        if state.learning or state.sigma <= 0:
            row["word"], row["range"] = "Learning your normal", "needs about 10 days"
        else:
            low, high = state.median - 2 * state.sigma, state.median + 2 * state.sigma
            row["range"] = f"usual {low:.{sig.decimals}f} to {high:.{sig.decimals}f}"
            row["status"], row["word"] = ("yellow", "Drifting") if state.flagged else ("green", "In your usual range")
    return row


def body_map(run: AstronautRun, series: dict[str, np.ndarray], day: int) -> dict[str, Any]:
    notes = guide()
    regions = []
    for region in REGIONS:
        rows = [_row(run, series, sid, day, notes) for sid in region["signals"] if sid in series]
        if region["system"]:
            sysday = run.systems[region["system"]][day - 1]
            status = "none" if sysday["learning"] else sysday["status"]
        elif region["id"] == "radiation":
            status = run.radiation[day - 1]["status"]
        else:
            status = max((r["status"] for r in rows), key=lambda s: RANK[s], default="none")
        if region["id"] == "radiation":
            rad = run.radiation[day - 1]
            rows.insert(0, {"id": "career", "name": "Career dose", "unit": "mSv", "value": rad["career_dose_msv"], "day": day,
                            "status": rad["status"], "word": "Near the limit" if rad["near_limit"] else "Below NASA's limit",
                            "range": f"NASA limit {rad['limit_msv']}", "guide": notes.get("daily_dose", {})})
        regions.append({k: region[k] for k in ("id", "name", "x", "y", "function", "hazards", "risks", "links")} | {"status": status, "readings": rows})
    tracked = sum(1 for _ in DRIFT_SIGNALS) + len(REFERENCE)
    return {"day": day, "regions": regions, "hazards": HAZARDS, "tracked": tracked}
