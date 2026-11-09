"""Read a small long-format CSV, shaped like a public OSDR table, into Vigil's schema and run the engine on it."""

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np
from app import config, db
from app.engine.drift import track_signal
from app.signals import BY_ID

IMPORT_SEED = -1  # marks imported rows in the readings table
ALIASES = {
    "subject": {"subject", "subject_id", "source name", "source_name", "crew_id"},
    "time": {"day", "timepoint", "time point", "time"},
    "measure": {"measure", "analyte", "parameter", "signal"},
    "value": {"value", "result"},
    "unit": {"unit", "units"},
}
MEASURES = {
    "crp": "crp", "c-reactive protein": "crp", "c reactive protein": "crp",
    "il-6": "il6", "il6": "il6", "interleukin-6": "il6", "interleukin 6": "il6",
    "lymphocytes": "lymph", "lymphocyte percent": "lymph", "lymphocytes %": "lymph",
    "body temperature": "temp", "temperature": "temp",
    "resting heart rate": "resting_hr", "heart rate": "resting_hr",
    "hrv": "hrv", "rmssd": "hrv",
    "systolic pressure": "bp_sys", "systolic": "bp_sys", "diastolic pressure": "bp_dia", "diastolic": "bp_dia",
    "spo2": "spo2", "grip strength": "grip", "lean mass": "lean_mass", "sleep duration": "sleep_hours",
}
# Multiply by this to reach the unit Vigil uses.
UNIT_FACTORS = {("crp", "mg/dl"): 10.0, ("lymph", "%"): 0.01}


@dataclass(frozen=True)
class Row:
    subject: str
    day: int
    signal: str
    value: float


@dataclass
class ImportResult:
    rows: list[Row] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def parse_time(text: str, flight_days: int) -> int:
    """Turn 92, L-92, FD3 or R+1 into a day number relative to launch."""
    text = text.strip().upper().replace(" ", "")
    if match := re.fullmatch(r"L-(\d+)", text):
        return -int(match[1])
    if match := re.fullmatch(r"FD(\d+)", text):
        return int(match[1])
    if match := re.fullmatch(r"R\+(\d+)", text):
        return flight_days + int(match[1])
    return int(float(text))


def find_columns(header: list[str]) -> dict[str, str]:
    columns: dict[str, str] = {}
    for name in header:
        for key, options in ALIASES.items():
            if name.strip().lower() in options:
                columns[key] = name
    missing = sorted({"subject", "time", "measure", "value"} - set(columns))
    if missing:
        raise ValueError(f"The file has no column for: {', '.join(missing)}")
    return columns


def read_csv(path: Path, flight_days: int) -> ImportResult:
    """Read every usable row and keep a plain reason for every row left out."""
    result = ImportResult()
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = find_columns(reader.fieldnames or [])
        for line, raw in enumerate(reader, start=2):
            measure = raw[columns["measure"]].strip()
            signal = MEASURES.get(measure.lower())
            if signal is None:
                result.skipped.append(f"Line {line}: Vigil does not track {measure}.")
                continue
            try:
                day = parse_time(raw[columns["time"]], flight_days)
                value = float(raw[columns["value"]])
            except ValueError:
                result.skipped.append(f"Line {line}: could not read the time or value.")
                continue
            unit = raw[columns["unit"]].strip().lower() if "unit" in columns else ""
            value *= UNIT_FACTORS.get((signal, unit), 1.0)
            spec = BY_ID[signal]
            if not spec.low <= value <= spec.high:
                result.skipped.append(f"Line {line}: {measure} value {value:g} is outside the plausible range.")
                continue
            result.rows.append(Row(raw[columns["subject"]].strip(), day, signal, value))
    return result


def analyse(rows: list[Row], cfg: config.Config) -> list[dict]:
    """Run the same detector the mission uses. Each reading counts as one observation."""
    report = []
    for subject, signal in sorted({(r.subject, r.signal) for r in rows}):
        readings = sorted((r for r in rows if r.subject == subject and r.signal == signal), key=lambda r: r.day)
        spec = BY_ID[signal]
        states = track_signal(spec, np.array([r.value for r in readings]), cfg)
        report.append({
            "subject": subject, "signal": signal, "readings": len(readings), "still_learning": states[-1].learning,
            "flagged_days": [r.day for r, s in zip(readings, states, strict=True) if s.flagged],
        })
    return report


def save(rows: list[Row]) -> None:
    with db.connect() as con:
        con.execute("DELETE FROM readings WHERE seed = ?", (IMPORT_SEED,))
        con.executemany(
            "INSERT OR REPLACE INTO readings VALUES (?,?,?,?,?)",
            [(IMPORT_SEED, f"import:{r.subject}", r.day, r.signal, r.value) for r in rows],
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--flight-days", type=int, default=3, help="flight length, used for R+ timepoints")
    args = parser.parse_args()
    result = read_csv(args.csv_file, args.flight_days)
    save(result.rows)
    print(f"Imported {len(result.rows)} readings. Left out {len(result.skipped)} rows.")
    for reason in result.skipped:
        print(f"  {reason}")
    for row in analyse(result.rows, config.load_config()):
        state = "still learning" if row["still_learning"] else f"flagged on days {row['flagged_days']}" if row["flagged_days"] else "no drift"
        print(f"  {row['subject']} {row['signal']}: {row['readings']} readings, {state}")


if __name__ == "__main__":
    main()
