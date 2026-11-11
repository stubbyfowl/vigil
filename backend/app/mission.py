"""A real mission: readings people enter or import, shaped into the same series the engine reads."""

import csv
import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from sqlite3 import Connection

import numpy as np

from .signals import BY_ID, SIGNALS, Signal
from .sim.generator import Astronaut, Mission

HOURS = 24
CHECKIN_SIGNALS = ("mood", "energy", "stress", "symptoms", "journal")
DERIVED = ("cum_dose", "spe_flag")
# What a person or the Medical Officer can type in. Check-in scales come from the check-in screen.
LOGGABLE: list[Signal] = [s for s in SIGNALS if s.id not in CHECKIN_SIGNALS and s.id not in DERIVED]
# A file may also carry check-in scales, for example from an analog mission.
IMPORTABLE = {s.id for s in SIGNALS if s.id not in DERIVED and s.id != "journal"}
ALIASES = {
    "heart rate": "resting_hr", "resting heart rate": "resting_hr", "rhr": "resting_hr", "rmssd": "hrv",
    "systolic": "bp_sys", "diastolic": "bp_dia", "oxygen": "spo2", "blood oxygen": "spo2",
    "temperature": "temp", "body temperature": "temp", "sleep": "sleep_hours", "sleep duration": "sleep_hours",
    "c-reactive protein": "crp", "interleukin-6": "il6", "il-6": "il6", "dose": "daily_dose",
}
MAX_IMPORT_ROWS = 50_000
MAX_SKIP_REASONS = 30


def mission_day(start: date, today: date) -> int:
    """Day 1 is the start date."""
    return (today - start).days + 1


def day_date(start: date, day: int) -> date:
    return start + timedelta(days=day - 1)


def check_value(signal_id: str, value: object, allowed: set[str] | None = None) -> float:
    """Return the value as a number, or raise with a sentence a person can act on."""
    sig = BY_ID.get(signal_id)
    if sig is None or (allowed is not None and signal_id not in allowed):
        raise ValueError(f"{signal_id} is not a reading Vigil tracks.")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError(f"{sig.name} needs a number.") from None
    if not math.isfinite(number) or not sig.low <= number <= sig.high:
        raise ValueError(f"{sig.name} must be from {sig.low:g} to {sig.high:g} {sig.unit}.")
    return number


def _forward_fill(values: np.ndarray) -> np.ndarray:
    out = values.copy()
    last = math.nan
    for i, v in enumerate(out):
        if math.isnan(v):
            out[i] = last
        else:
            last = v
    return np.nan_to_num(out, nan=0.0)


def build(con: Connection, crew: tuple[Astronaut, ...], days: int) -> Mission:
    """One array per signal per person. A day with several readings uses their median."""
    series: dict[str, dict[str, np.ndarray]] = {}
    hourly: dict[str, np.ndarray] = {}
    for who in crew:
        s = {sig.id: np.full(days, np.nan) for sig in SIGNALS}
        grouped: dict[tuple[str, int], list[float]] = {}
        rows = con.execute("SELECT signal, day, value FROM entries WHERE member = ? AND day BETWEEN 1 AND ?", (who.id, days))
        for row in rows:
            grouped.setdefault((row["signal"], row["day"]), []).append(row["value"])
        for (signal, day), values in grouped.items():
            if signal in s:
                s[signal][day - 1] = float(np.median(values))
        # A dosimeter may report a rate, a daily total, or both. A rate becomes a total for that day.
        estimate = s["dose_rate"] * HOURS / 1000
        s["daily_dose"] = np.where(np.isnan(s["daily_dose"]), estimate, s["daily_dose"])
        s["cum_dose"] = np.nancumsum(s["daily_dose"])
        s["spe_flag"] = np.zeros(days)
        hourly[who.id] = np.repeat(_forward_fill(s["dose_rate"]), HOURS)
        series[who.id] = s
    return Mission(0, days, series, hourly, {k: v.copy() for k, v in hourly.items()}, None, [])


@dataclass
class ImportResult:
    rows: list[tuple[str, str, float, int]] = field(default_factory=list)  # member, signal, value, day
    skipped: list[str] = field(default_factory=list)
    skipped_count: int = 0

    def skip(self, reason: str) -> None:
        self.skipped_count += 1
        if len(self.skipped) < MAX_SKIP_REASONS:
            self.skipped.append(reason)


def _signal_for(text: str) -> str | None:
    key = text.strip().lower()
    if key in BY_ID:
        return key
    if key in ALIASES:
        return ALIASES[key]
    return next((s.id for s in SIGNALS if s.name.lower() == key), None)


def _day_for(row: dict[str, str], start: date, today_day: int) -> int:
    if (row.get("date") or "").strip():
        return mission_day(start, date.fromisoformat(row["date"].strip()[:10]))
    if (row.get("day") or "").strip():
        return int(float(row["day"]))
    raise ValueError("needs a date or a mission day")


def read_import(path: Path, start: date, today_day: int, members: dict[str, str], default_member: str | None) -> ImportResult:
    """Read a CSV with date (or day), signal and value, and optionally member.

    Every row that cannot be used gets a plain reason. Nothing is written here.
    """
    result = ImportResult()
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = {(h or "").strip().lower(): h for h in reader.fieldnames or []}
        missing = [c for c in ("signal", "value") if c not in header]
        if "date" not in header and "day" not in header:
            missing.append("date")
        if missing:
            raise ValueError(f"The file needs these columns: {', '.join(missing)}.")
        if "member" not in header and default_member is None:
            raise ValueError("The file needs a member column, because it is not tied to one person.")
        for number, raw in enumerate(reader, start=2):
            if number > MAX_IMPORT_ROWS + 1:
                result.skip(f"Stopped after {MAX_IMPORT_ROWS} rows.")
                break
            row = {k: (raw.get(v) or "") for k, v in header.items()}
            who_text = row.get("member", "").strip().lower()
            member = members.get(who_text) if who_text else default_member
            if member is None:
                result.skip(f"Row {number}: no crew member named {row.get('member', '').strip()!r}.")
                continue
            signal = _signal_for(row["signal"])
            if signal is None or signal not in IMPORTABLE:
                result.skip(f"Row {number}: {row['signal'].strip()!r} is not a reading Vigil tracks.")
                continue
            try:
                day = _day_for(row, start, today_day)
                value = check_value(signal, row["value"], IMPORTABLE)
            except ValueError as err:
                result.skip(f"Row {number}: {err}")
                continue
            if day < 1:
                result.skip(f"Row {number}: the date is before the mission started.")
            elif day > today_day:
                result.skip(f"Row {number}: the date is in the future.")
            else:
                result.rows.append((member, signal, value, day))
    return result


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", text)[:80]
