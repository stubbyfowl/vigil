"""A real mission: readings people enter or import, shaped into the same series the engine reads."""

import csv
import math
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from sqlite3 import Connection
from typing import IO
from xml.etree.ElementTree import iterparse  # noqa: S405 (expat in Python 3.12 limits entity expansion)

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
# Apple Health export.xml record types Vigil can read, and what each becomes.
APPLE_TYPES = {
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
    "HKQuantityTypeIdentifierOxygenSaturation": "spo2",
    "HKQuantityTypeIdentifierBodyTemperature": "temp",
    "HKQuantityTypeIdentifierBloodPressureSystolic": "bp_sys",
    "HKQuantityTypeIdentifierBloodPressureDiastolic": "bp_dia",
}
APPLE_SLEEP = "HKCategoryTypeIdentifierSleepAnalysis"
APPLE_ASLEEP = {
    "HKCategoryValueSleepAnalysisAsleep", "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleepCore", "HKCategoryValueSleepAnalysisAsleepDeep", "HKCategoryValueSleepAnalysisAsleepREM",
}
APPLE_HRV = "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"


def mission_day(start: date, today: date) -> int:
    """Day 1 is the start date."""
    return (today - start).days + 1


def day_date(start: date, day: int) -> date:
    return start + timedelta(days=day - 1)


def check_value(signal_id: str, value: object, allowed: set[str] | None = None) -> float:
    """Return the value as a number, or raise with a sentence that says what to fix."""
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
        wide = {h: _signal_for(h) for h in header if h not in ("date", "day", "member", "unit")}
        if "signal" not in header and "value" not in header and any(wide.values()):
            return _read_wide(reader, header, wide, start, today_day, members, default_member, result)
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


def _read_wide(reader: csv.DictReader, header: dict[str, str], wide: dict[str, str | None], start: date, today_day: int,
               members: dict[str, str], default_member: str | None, result: ImportResult) -> ImportResult:
    """A spreadsheet with a date column and one column per reading."""
    if "date" not in header and "day" not in header:
        raise ValueError("The file needs a date or day column.")
    unknown = [h for h, sig in wide.items() if sig is None or sig not in IMPORTABLE]
    if unknown:
        result.skip(f"Columns left out because Vigil does not track them: {', '.join(unknown)}.")
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
        try:
            day = _day_for(row, start, today_day)
        except ValueError as err:
            result.skip(f"Row {number}: {err}")
            continue
        if not 1 <= day <= today_day:
            result.skip(f"Row {number}: the date is outside the mission so far.")
            continue
        for column, signal in wide.items():
            text = row.get(column, "").strip()
            if not text or signal is None or signal not in IMPORTABLE:
                continue
            try:
                result.rows.append((member, signal, check_value(signal, text, IMPORTABLE), day))
            except ValueError as err:
                result.skip(f"Row {number}: {err}")
    return result


def _apple_records(stream: IO[bytes]) -> Iterator[dict[str, str]]:
    for _, element in iterparse(stream, events=("end",)):  # noqa: S314
        if element.tag == "Record":
            yield dict(element.attrib)
        element.clear()


def _apple_value(signal: str, unit: str, value: float) -> float:
    """Apple stores oxygen as a fraction and lets temperature be in Fahrenheit."""
    if signal == "spo2" and value <= 1:
        return value * 100
    if signal == "temp" and unit.lower() in ("degf", "\u00b0f", "f"):
        return (value - 32) * 5 / 9
    return value


def read_apple_health(path: Path, start: date, today_day: int, member: str) -> ImportResult:
    """Read an Apple Health export (export.xml, or the export.zip around it) for one person.

    Readings outside the mission so far are counted, not listed. Sleep is summed per night and
    filed under the morning it ended. Apple's HRV is SDNN, a different measure from Vigil's RMSSD, so it is left out.
    """
    result = ImportResult()
    outside = hrv = 0
    sleep: dict[int, float] = {}

    def day_of(stamp_text: str) -> int:
        return mission_day(start, date.fromisoformat(stamp_text.strip()[:10]))

    def consume(stream: IO[bytes]) -> None:
        nonlocal outside, hrv
        for count, rec in enumerate(_apple_records(stream)):
            if count > MAX_IMPORT_ROWS * 20:
                result.skip("Stopped after a million records.")
                return
            kind = rec.get("type", "")
            if kind == APPLE_HRV:
                hrv += 1
                continue
            if kind == APPLE_SLEEP and rec.get("value") in APPLE_ASLEEP:
                try:
                    begin = datetime.strptime(rec["startDate"][:19], "%Y-%m-%d %H:%M:%S")
                    end = datetime.strptime(rec["endDate"][:19], "%Y-%m-%d %H:%M:%S")
                    day = day_of(rec["endDate"])
                except (KeyError, ValueError):
                    result.skip("A sleep record had an unreadable date.")
                    continue
                if 1 <= day <= today_day:
                    sleep[day] = sleep.get(day, 0.0) + max(0.0, (end - begin).total_seconds() / 3600)
                else:
                    outside += 1
                continue
            signal = APPLE_TYPES.get(kind)
            if signal is None:
                continue
            try:
                day = day_of(rec["startDate"])
                value = check_value(signal, _apple_value(signal, rec.get("unit", ""), float(rec["value"])), IMPORTABLE)
            except (KeyError, ValueError) as err:
                result.skip(f"{BY_ID[signal].name}: {err}")
                continue
            if 1 <= day <= today_day:
                result.rows.append((member, signal, value, day))
            else:
                outside += 1

    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            inner = next((n for n in archive.namelist() if n.endswith("export.xml")), None)
            if inner is None:
                raise ValueError("The zip file has no export.xml inside.")
            with archive.open(inner) as stream:
                consume(stream)
    else:
        with path.open("rb") as stream:
            consume(stream)
    for day, hours in sorted(sleep.items()):
        try:
            result.rows.append((member, "sleep_hours", check_value("sleep_hours", round(hours, 2), IMPORTABLE), day))
        except ValueError as err:
            result.skip(f"Night before day {day}: {err}")
    if outside:
        result.skip(f"{outside} readings were from outside the mission so far and were left out.")
    if hrv:
        result.skip(f"{hrv} heart rate variability readings were left out. Apple records SDNN, and Vigil tracks RMSSD.")
    return result
