"""The source catalog stays in step with SOURCES.md, and device exports import correctly. All test data is invented."""

import importlib.util
import zipfile
from datetime import date

import pytest
from app import config
from app.mission import read_apple_health, read_import
from app.views import Vigil

START = date(2026, 11, 1)
TODAY_DAY = 10
APPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData [
<!ELEMENT HealthData (Record*)>
<!ATTLIST Record type CDATA #REQUIRED>
]>
<HealthData locale="en_US">
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" unit="count/min" value="58" startDate="2026-11-03 07:00:00 -0700" endDate="2026-11-03 07:00:00 -0700"/>
 <Record type="HKQuantityTypeIdentifierOxygenSaturation" unit="%" value="0.97" startDate="2026-11-03 08:00:00 -0700" endDate="2026-11-03 08:00:00 -0700"/>
 <Record type="HKQuantityTypeIdentifierBodyTemperature" unit="degF" value="98.6" startDate="2026-11-04 08:00:00 -0700" endDate="2026-11-04 08:00:00 -0700"/>
 <Record type="HKQuantityTypeIdentifierBloodPressureSystolic" unit="mmHg" value="118" startDate="2026-11-04 09:00:00 -0700" endDate="2026-11-04 09:00:00 -0700"/>
 <Record type="HKQuantityTypeIdentifierBloodPressureDiastolic" unit="mmHg" value="76" startDate="2026-11-04 09:00:00 -0700" endDate="2026-11-04 09:00:00 -0700"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" value="HKCategoryValueSleepAnalysisAsleepCore" startDate="2026-11-04 23:30:00 -0700" endDate="2026-11-05 03:30:00 -0700"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" value="HKCategoryValueSleepAnalysisAsleepREM" startDate="2026-11-05 03:30:00 -0700" endDate="2026-11-05 05:30:00 -0700"/>
 <Record type="HKCategoryTypeIdentifierSleepAnalysis" value="HKCategoryValueSleepAnalysisInBed" startDate="2026-11-04 23:00:00 -0700" endDate="2026-11-05 06:00:00 -0700"/>
 <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" unit="ms" value="45" startDate="2026-11-04 03:00:00 -0700" endDate="2026-11-04 03:00:00 -0700"/>
 <Record type="HKQuantityTypeIdentifierRestingHeartRate" unit="count/min" value="61" startDate="2025-01-01 07:00:00 -0700" endDate="2025-01-01 07:00:00 -0700"/>
 <Record type="HKQuantityTypeIdentifierStepCount" unit="count" value="5000" startDate="2026-11-04 09:00:00 -0700" endDate="2026-11-04 10:00:00 -0700"/>
</HealthData>
"""


def test_sources_md_is_generated_from_the_catalog():
    spec = importlib.util.spec_from_file_location("build_sources", config.ROOT / "scripts" / "build_sources.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (config.ROOT / "SOURCES.md").read_text() == module.render(), "Run scripts/build_sources.py"


def by_signal(result):
    return {(signal, day): value for _, signal, value, day in result.rows}


@pytest.mark.parametrize("zipped", [False, True])
def test_apple_health_export_imports(tmp_path, zipped):
    xml = tmp_path / "export.xml"
    xml.write_text(APPLE_XML)
    path = xml
    if zipped:
        path = tmp_path / "export.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.write(xml, "apple_health_export/export.xml")
    result = read_apple_health(path, START, TODAY_DAY, "lena")
    got = by_signal(result)
    assert got[("resting_hr", 3)] == 58 and got[("spo2", 3)] == 97
    assert got[("temp", 4)] == pytest.approx(37.0)
    assert got[("bp_sys", 4)] == 118 and got[("bp_dia", 4)] == 76
    assert got[("sleep_hours", 5)] == pytest.approx(6.0)  # core and REM count, time in bed does not
    assert {m for m, *_ in result.rows} == {"lena"}
    reasons = " ".join(result.skipped)
    assert "SDNN" in reasons and "outside the mission" in reasons


def test_apple_zip_without_export_is_refused(tmp_path):
    path = tmp_path / "export.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("other.txt", "nothing")
    with pytest.raises(ValueError, match="export.xml"):
        read_apple_health(path, START, TODAY_DAY, "lena")


def test_wide_spreadsheet_imports_and_explains_unknown_columns(tmp_path):
    path = tmp_path / "watch.csv"
    path.write_text("date,Resting heart rate,SpO2,steps\n2026-11-02,57,98,4000\n2026-11-03,59,,5100\n2026-11-30,60,97,1\n2026-11-04,500,97,1\n")
    result = read_import(path, START, TODAY_DAY, {"lena": "lena"}, "lena")
    got = by_signal(result)
    assert got == {("resting_hr", 2): 57, ("spo2", 2): 98, ("resting_hr", 3): 59, ("spo2", 4): 97}
    reasons = " ".join(result.skipped)
    assert "steps" in reasons and "outside the mission" in reasons and "Resting heart rate must be" in reasons


def test_import_folder_accepts_apple_exports(tmp_path, monkeypatch):
    for name, sub in (("MISSION_DB_PATH", "mission.db"), ("OUTBOX_DIR", "outbox"), ("IMPORT_DIR", "import"), ("EXPORT_DIR", "exports"), ("BACKUP_DIR", "backups")):
        monkeypatch.setattr(config, name, tmp_path / sub)
    today = [date(2026, 11, 10)]
    v = Vigil(today=lambda: today[0])
    v.setup_mission("Analog 1", "2026-11-01", 30, "Ana Reyes", "4826")
    v.request({"id": "ana", "role": "commander"}, "add_member", {"name": "Lena Novak", "role": "crew", "pin": "5170"})
    config.IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    (config.IMPORT_DIR / "export.xml").write_text(APPLE_XML)
    lena = {"id": "lena", "role": "crew"}
    assert [f["name"] for f in v.request(lena, "import_files", {})["files"]] == ["export.xml"]
    out = v.request(lena, "import_file", {"file": "export.xml"})
    assert out["imported"] == 6 and out["members"] == ["lena"]
    assert {e["signal"] for e in v.request(lena, "entries", {})["entries"]} == {"resting_hr", "spo2", "temp", "bp_sys", "bp_dia", "sleep_hours"}
