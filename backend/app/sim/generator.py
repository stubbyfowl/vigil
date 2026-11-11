"""Synthetic crew generator. The same seed always gives the same mission."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path

import numpy as np

from ..signals import DRIFT_SIGNALS, Signal

HOURS = 24
SHELTER_FACTOR = 0.4  # invented value, see SOURCES.md
# Storms replay a real event from NOAA's solar proton event list (data/space_weather).
# Start time, rise to peak and relative size come from the list. The step from proton flux
# to dose rate inside this ship is a team assumption, not a measurement.
EVENT_CATALOG = Path(__file__).resolve().parents[3] / "data" / "space_weather" / "noaa_solar_proton_events.json"
REFERENCE_EVENT = "1989-10-19"  # the October 1989 events define NASA's storm shielding limit [V1 4031]
FREE_SPACE_USV_H_PER_PFU = 0.025  # team assumption, must_verify
STORM_DECAY_RISES = 2.0  # the flux falls back over about two rise times, team assumption
BASE_DOSE_RATE = 76.0  # about 1.8 mSv per day in Mars cruise (Curiosity RAD, Zeitlin 2013)
MISSING_RATE = 0.03


@dataclass(frozen=True)
class Astronaut:
    id: str
    name: str
    role: str
    tag: str
    prior_dose: float  # career dose before this mission, mSv
    offsets: dict[str, float] = field(default_factory=dict)  # fixed baseline offsets, in population sd
    control: bool = False


CREW = (
    Astronaut("cmdr", "Ana Reyes", "Commander", "CMD", 190, {"resting_hr": -1.1}),
    Astronaut("plt", "Tomas Okafor", "Pilot", "PLT", 80, {"resting_hr": 0.3}),
    Astronaut("mo", "Priya Nair", "Medical Officer", "MO", 120),
    Astronaut("eng", "Lena Novak", "Engineer", "ENG", 60),
    Astronaut("ctl", "Kai Sato", "Quiet control", "CTL", 40, control=True),
)


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    day: int
    astronaut: str
    system: str
    ramp: int
    duration: int
    changes: dict[str, float]


EVENTS = (
    Event("immune_stress", "Immune stress", 40, "eng", "immune", 3, 14,
          {"temp": 0.35, "crp": 2.5, "il6": 2.2, "sleep_eff": -6.0}),
    Event("behavior_slide", "Behavioral slide", 90, "plt", "behavior", 5, 21,
          {"sleep_hours": -1.2, "mood": -2.0, "social_min": -45.0, "stress": 2.0}),
    Event("heart_drift", "Heart drift", 150, "cmdr", "heart", 8, 31,
          {"resting_hr": 8.0, "hrv": -16.0, "ortho_rise": 7.0}),
)
STORM_DAY = 120
STORM_START_HOUR = 6  # hour of the day the storm reaches the ship
STORM_WARNING_HOURS = 2


@dataclass
class Mission:
    seed: int
    days: int
    series: dict[str, dict[str, np.ndarray]]
    hourly: dict[str, np.ndarray]  # measured dose rate per hour, per person
    hourly_free: dict[str, np.ndarray]  # same hours with no shelter
    storm: dict[str, int] | None
    ground_truth: list[dict]


def event_profile(ev: Event, days: int) -> np.ndarray:
    """Strength of an event from 0 to 1 for each mission day."""
    t = np.arange(1, days + 1)
    rise = np.clip((t - ev.day + 1) / ev.ramp, 0, 1)
    fall = np.clip(1 - (t - (ev.day + ev.duration) + 1) / ev.ramp, 0, 1)
    return rise * fall


def _ar_noise(rng: np.random.Generator, days: int) -> np.ndarray:
    """Unit variance noise where each day leans a little on the day before."""
    phi = 0.3
    shocks = rng.normal(0, 1, days)
    noise = np.zeros(days)
    noise[0] = shocks[0]
    for i in range(1, days):
        noise[i] = phi * noise[i - 1] + np.sqrt(1 - phi**2) * shocks[i]
    return noise


def _personal_baseline(sig: Signal, who: Astronaut, rng: np.random.Generator) -> float:
    offset = who.offsets[sig.id] + rng.normal(0, 0.1) if sig.id in who.offsets else rng.normal(0, 1)
    return sig.pop_mean + float(np.clip(offset, -2, 2)) * sig.pop_sd


def _signal_series(sig: Signal, who: Astronaut, days: int, rng: np.random.Generator, planted: bool) -> np.ndarray:
    t = np.arange(days)
    base = _personal_baseline(sig, who, rng)
    noise = sig.noise * rng.uniform(0.85, 1.15) * _ar_noise(rng, days)
    rhythm = 0.35 * sig.noise * np.sin(2 * np.pi * (t + rng.integers(0, 7)) / 7)
    values = base + noise + rhythm + sig.trend * t / 180
    if planted:
        for ev in EVENTS:
            if ev.astronaut == who.id and sig.id in ev.changes:
                values += ev.changes[sig.id] * event_profile(ev, days)
    values = np.round(np.clip(values, sig.low, sig.high), sig.decimals)
    observed = (t - rng.integers(0, sig.cadence)) % sig.cadence == 0
    values[~observed | (rng.random(days) < MISSING_RATE)] = np.nan
    return values


@cache
def solar_events() -> tuple[dict, ...]:
    """NOAA's list of solar proton events since 1976, bundled with Vigil."""
    return tuple(json.loads(EVENT_CATALOG.read_text())["events"])


def reference_event(date: str = REFERENCE_EVENT) -> dict:
    """The catalog event that starts on this date. The largest one if several do."""
    matches = [e for e in solar_events() if e["begin"].startswith(date)]
    if not matches:
        raise LookupError(f"No solar proton event starts on {date} in NOAA's list.")
    event = max(matches, key=lambda e: e["peak_pfu"])
    parse = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%MZ")  # noqa: E731
    rise = max(1, round((parse(event["peak_time"]) - parse(event["begin"])).total_seconds() / 3600))
    return event | {"rise_hours": rise, "peak_usv_h": round(event["peak_pfu"] * FREE_SPACE_USV_H_PER_PFU, 1)}


def _storm_window(days: int, event: dict) -> dict | None:
    if days < STORM_DAY + 2:
        return None
    onset = (STORM_DAY - 1) * HOURS + STORM_START_HOUR
    length = int(event["rise_hours"] * (1 + STORM_DECAY_RISES) + 0.5)
    return {
        "warning_hour": onset - STORM_WARNING_HOURS, "onset_hour": onset, "end_hour": onset + length,
        "rise_hours": event["rise_hours"], "peak_usv_h": event["peak_usv_h"], "event_begin": event["begin"],
        "event_peak_pfu": event["peak_pfu"], "event_flare": event["flare"],
    }


def _free_space_hourly(days: int, storm: dict | None, rng: np.random.Generator) -> np.ndarray:
    """Dose rate per hour outside any storm shelter. Same for the whole ship."""
    hours = days * HOURS
    slow = 1 + 0.04 * np.sin(2 * np.pi * np.arange(hours) / (27 * HOURS))
    rate = BASE_DOSE_RATE * slow + rng.normal(0, 3.0, hours)
    if storm:
        rise = storm["rise_hours"]
        h = np.arange(storm["end_hour"] - storm["onset_hour"], dtype=float)
        shape = np.minimum(h / rise, 1) * np.exp(-np.maximum(h - rise, 0) / (rise * STORM_DECAY_RISES / 3))
        rate[storm["onset_hour"]:storm["end_hour"]] += storm["peak_usv_h"] * shape
    return np.clip(rate, 0, None)


def _radiation_series(
    free: np.ndarray, storm: dict[str, int] | None, days: int, rng: np.random.Generator
) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
    """Turn the ship's dose rate into one person's dosimeter readings."""
    personal_free = free * rng.uniform(0.95, 1.05)
    measured = personal_free.copy()
    in_storm = np.zeros(days * HOURS, dtype=bool)
    if storm:
        in_storm[storm["onset_hour"]:storm["end_hour"]] = True
        # The crew takes one hour to reach the shelter.
        measured[storm["onset_hour"] + 1:storm["end_hour"]] *= SHELTER_FACTOR
    by_day = measured.reshape(days, HOURS)
    daily_dose = np.round(by_day.sum(axis=1) / 1000, 3)
    series = {
        "dose_rate": np.round(by_day.mean(axis=1), 1),
        "daily_dose": daily_dose,
        "cum_dose": np.round(np.cumsum(daily_dose), 2),
        "spe_flag": in_storm.reshape(days, HOURS).any(axis=1).astype(float),
    }
    return series, measured, personal_free


def build_ground_truth(days: int, storm: dict[str, int] | None, planted: bool) -> list[dict]:
    """The answer key for evaluation."""
    if not planted:
        return []
    truth: list[dict] = [
        {
            "id": ev.id, "title": ev.title, "day": ev.day, "astronaut": ev.astronaut, "system": ev.system,
            "ramp_days": ev.ramp, "duration_days": ev.duration,
            "signals": [{"signal": k, "change": v} for k, v in ev.changes.items()],
        }
        for ev in EVENTS if ev.day <= days
    ]
    if storm:
        truth.append({
            "id": "solar_storm", "title": "Solar particle event", "day": STORM_DAY, "astronaut": "all",
            "system": "radiation", "ramp_days": 0, "duration_days": round((storm["end_hour"] - storm["onset_hour"]) / HOURS, 2),
            "signals": [{"signal": "dose_rate", "change": storm["peak_usv_h"]}], **storm,
        })
    return sorted(truth, key=lambda e: e["day"])


def generate_mission(seed: int = 42, days: int = 180, planted: bool = True, storm_event: str = REFERENCE_EVENT) -> Mission:
    """Build a full mission. Set planted=False for a mission with no events.

    storm_event is the start date of the NOAA-listed solar proton event the day-120 storm replays.
    """
    series: dict[str, dict[str, np.ndarray]] = {}
    hourly: dict[str, np.ndarray] = {}
    hourly_free: dict[str, np.ndarray] = {}
    storm = _storm_window(days, reference_event(storm_event)) if planted else None
    free = _free_space_hourly(days, storm, np.random.default_rng([seed, 999]))
    for index, who in enumerate(CREW):
        rng = np.random.default_rng([seed, index])
        series[who.id] = {s.id: _signal_series(s, who, days, rng, planted) for s in DRIFT_SIGNALS}
        rad, hourly[who.id], hourly_free[who.id] = _radiation_series(free, storm, days, rng)
        series[who.id].update(rad)
    return Mission(seed, days, series, hourly, hourly_free, storm, build_ground_truth(days, storm, planted))
