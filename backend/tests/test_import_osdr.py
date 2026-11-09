import sqlite3
from pathlib import Path

import pytest
from scripts import import_osdr as imp

from app import config

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "samples" / "osdr_style_sample.csv"


@pytest.mark.parametrize("text,expected", [("L-92", -92), ("l-3", -3), ("FD3", 3), ("R+1", 4), ("12", 12), ("12.0", 12)])
def test_time_labels(text, expected):
    assert imp.parse_time(text, 3) == expected


def test_bad_time_is_rejected():
    with pytest.raises(ValueError):
        imp.parse_time("soon", 3)


def test_sample_imports_and_explains_what_it_left_out():
    result = imp.read_csv(SAMPLE, 3)
    assert len(result.rows) == 24
    text = " ".join(result.skipped)
    assert "Albumin" in text and "could not read" in text and "outside the plausible range" in text
    assert len(result.skipped) == 3


def test_units_are_converted():
    rows = imp.read_csv(SAMPLE, 3).rows
    assert next(r for r in rows if r.subject == "SUBJ-B" and r.signal == "crp").value == pytest.approx(1.1)
    assert next(r for r in rows if r.signal == "lymph").value == pytest.approx(0.33)


def test_engine_flags_the_planted_rise_only():
    report = {(r["subject"], r["signal"]): r for r in imp.analyse(imp.read_csv(SAMPLE, 3).rows, config.load_config())}
    assert report[("SUBJ-A", "crp")]["flagged_days"][0] == 3
    assert report[("SUBJ-A", "il6")]["flagged_days"] == []
    assert report[("SUBJ-B", "crp")]["still_learning"]


def test_missing_column_says_which(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Source Name,Timepoint\nA,L-1\n")
    with pytest.raises(ValueError, match="measure, value"):
        imp.read_csv(bad, 3)


def test_rows_land_in_the_same_table():
    imp.save(imp.read_csv(SAMPLE, 3).rows)
    with sqlite3.connect(config.DB_PATH) as con:
        count = con.execute("SELECT COUNT(*) FROM readings WHERE seed = ? AND astronaut = 'import:SUBJ-A'", (imp.IMPORT_SEED,)).fetchone()[0]
    assert count == 21
