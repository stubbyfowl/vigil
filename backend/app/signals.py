"""Every tracked signal lives here. Adding a signal is one S(...) line."""

from dataclasses import dataclass

SYSTEMS = {
    "immune": "Immune",
    "bone": "Bone and Muscle",
    "heart": "Heart",
    "behavior": "Behavior",
}
RADIATION = "radiation"
DIET = "diet"  # self-reported food from the check-in. Feeds Gut City only, never an alert.


@dataclass(frozen=True)
class Signal:
    """Config for one health indicator. Where a population figure has a source, the comment names
    its id in data/sources.json. Noise, spread between people and event sizes are the team's."""

    id: str
    name: str
    unit: str
    system: str
    cadence: int  # days between readings
    low: float  # plausible range, used to clip generated data
    high: float
    noise: float  # day to day noise (1 sd)
    bad: str  # "up" or "down": the direction that is bad
    pop_mean: float  # synthetic population mean
    pop_sd: float  # spread of personal baselines between people
    trend: float = 0.0  # slow change over a full mission
    decimals: int = 1
    also: tuple[str, ...] = ()  # other systems this signal supports


S = Signal
SIGNALS: list[Signal] = [
    # Heart
    S("resting_hr", "Resting heart rate", "bpm", "heart", 1, 35, 140, 1.8, "up", 62, 7, 3.0, 0),  # hr_normal: 60 to 100
    S("hrv", "Heart rate variability", "ms", "heart", 1, 10, 150, 5.0, "down", 42, 15, -4.0, 0),  # nunan_hrv: 42, SD 15
    S("bp_sys", "Systolic pressure", "mmHg", "heart", 1, 80, 190, 4.0, "up", 116, 8, 2.0, 0),
    S("bp_dia", "Diastolic pressure", "mmHg", "heart", 1, 45, 120, 3.0, "up", 74, 6, 1.0, 0),
    S("ortho_rise", "Standing heart rate rise", "bpm", "heart", 1, 0, 60, 2.2, "up", 14, 3, 1.0, 0),
    S("spo2", "Blood oxygen", "%", "heart", 1, 80, 100, 0.4, "down", 98, 0.5),
    # Bone and muscle
    S("exercise_min", "Resistive exercise", "min", "bone", 1, 0, 240, 12, "down", 120, 15, 0, 0),  # nasa_exercise: about 2 h
    S("exercise_load", "Exercise load", "AU", "bone", 1, 0, 200, 8, "down", 100, 15, -3.0, 0),
    S("grip", "Grip strength", "kg", "bone", 7, 15, 80, 1.0, "down", 41, 10, -1.5),  # dodds_2014: medians 51 and 31
    S("bone_marker", "Bone marker index", "index", "bone", 14, 40, 160, 3.0, "down", 100, 10, -7.5),  # bone_meta_2020: 1.25%/month
    S("lean_mass", "Lean mass proxy", "kg", "bone", 7, 35, 95, 0.3, "down", 62, 8, -1.2),
    # Immune
    S("temp", "Body temperature", "°C", "immune", 1, 35, 41, 0.12, "up", 36.8, 0.2, 0, 2),  # mackowiak_1992
    S("crp", "CRP", "mg/L", "immune", 7, 0, 40, 0.2, "up", 1.0, 0.3, 0, 2),
    S("il6", "IL-6", "pg/mL", "immune", 7, 0, 40, 0.3, "up", 1.8, 0.4, 0, 2),
    S("lymph", "Lymphocyte ratio", "ratio", "immune", 7, 0.05, 0.7, 0.015, "down", 0.32, 0.04, 0, 3),
    S("symptoms", "Symptoms", "0 to 5", "immune", 1, 0, 5, 0.5, "up", 0.4, 0.15, 0, 0),
    # Behavior and sleep
    S("sleep_hours", "Sleep", "hours", "behavior", 1, 0, 12, 0.45, "down", 6.1, 0.5),  # barger_2014: 6.09 h on the ISS
    S("sleep_eff", "Sleep efficiency", "%", "behavior", 1, 40, 100, 2.0, "down", 88, 3, 0, 0, ("immune",)),
    S("mood", "Mood", "1 to 10", "behavior", 1, 1, 10, 0.7, "down", 7.0, 0.7, -0.4),
    S("stress", "Stress", "1 to 10", "behavior", 1, 1, 10, 0.7, "up", 4.0, 0.7, 0.4),
    S("energy", "Energy", "1 to 10", "behavior", 1, 1, 10, 0.7, "down", 7.0, 0.7, -0.3),
    S("social_min", "Social contact", "min", "behavior", 1, 0, 300, 18, "down", 90, 20, 0, 0),
    S("journal", "Journal tone", "-1 to 1", "behavior", 1, -1, 1, 0.15, "down", 0.25, 0.1, 0, 2),
    # Food, answered in the check-in. Servings per day, 0 to 5.
    S("fiber", "Fiber", "servings", DIET, 1, 0, 5, 1.0, "down", 3.0, 0.7, 0, 0),
    S("processed", "Processed food", "servings", DIET, 1, 0, 5, 1.0, "up", 1.5, 0.6, 0, 0),
    # Radiation is measured, not drift tested. The radiation module scores it.
    S("dose_rate", "Dose rate", "uSv/h", RADIATION, 1, 0, 2000, 3.0, "up", 76, 0),
    S("daily_dose", "Daily dose", "mSv", RADIATION, 1, 0, 50, 0.05, "up", 1.8, 0, 0, 2),
    S("cum_dose", "Mission dose", "mSv", RADIATION, 1, 0, 2000, 0, "up", 0, 0, 0, 1),
    S("spe_flag", "Solar particle event", "flag", RADIATION, 1, 0, 1, 0, "up", 0, 0, 0, 0),
]

BY_ID = {s.id: s for s in SIGNALS}
DRIFT_SIGNALS = [s for s in SIGNALS if s.system in SYSTEMS]
