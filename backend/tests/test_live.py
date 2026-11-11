"""A real mission from end to end: setup, accounts, readings, import, packets, export and access rules."""

import csv
import json
import random
import sqlite3
from datetime import date

import pytest
from app import config
from app.views import Vigil

BOSS = {"id": "ana", "role": "commander"}
MO = {"id": "priya", "role": "medical"}
LENA = {"id": "lena", "role": "crew"}
GROUND = {"id": "okafor", "role": "ground"}
DRIFT_FROM_DAY = 12


def point_at(mp, home):
    for name, sub in (("MISSION_DB_PATH", "mission.db"), ("OUTBOX_DIR", "outbox"), ("IMPORT_DIR", "import"),
                      ("EXPORT_DIR", "exports"), ("BACKUP_DIR", "backups")):
        mp.setattr(config, name, home / sub)


def new_mission(today):
    v = Vigil(today=lambda: today[0])
    v.setup_mission("Analog 1", "2026-11-01", 30, "Ana Reyes", "4826", 190)
    return v


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """Fifteen days of Lena's readings. Her heart rate climbs from day 12."""
    with pytest.MonkeyPatch.context() as mp:
        point_at(mp, tmp_path_factory.mktemp("live"))
        today = [date(2026, 11, 1)]
        v = new_mission(today)
        v.request(BOSS, "add_member", {"name": "Priya Nair", "role": "medical", "pin": "7391"})
        v.request(BOSS, "add_member", {"name": "Lena Novak", "role": "crew", "pin": "5170"})
        v.request(BOSS, "add_member", {"name": "Dr. Okafor", "role": "ground", "pin": "8402"})
        rng = random.Random(3)
        for day in range(1, 16):
            today[0] = date(2026, 11, day)
            v.live.tick(0)
            rise = 9 if day >= DRIFT_FROM_DAY else 0
            v.request(LENA, "log_readings", {"values": {
                "resting_hr": round(58 + rng.gauss(0, 1.5) + rise, 1), "hrv": round(60 + rng.gauss(0, 4) - 2 * rise, 1),
                "temp": 36.7, "sleep_hours": 7.2, "dose_rate": 80,
            }})
            v.request(LENA, "checkin", {"mood": 7, "sleep_quality": 7, "energy": 7, "stress": 3, "symptoms": 0,
                                        "journal": "Good day" if day == 15 else "", "keep_text": day == 15})
        yield v, today


def test_setup_refuses_bad_details(tmp_path, monkeypatch):
    point_at(monkeypatch, tmp_path)
    v = Vigil(today=lambda: date(2026, 11, 10))
    for args, words in (
        (("", "2026-11-01", 30, "Ana", "4826"), "name"),
        (("A", "11/01/2026", 30, "Ana", "4826"), "year-month-day"),
        (("A", "2026-12-01", 30, "Ana", "4826"), "future"),
        (("A", "2026-01-01", 30, "Ana", "4826"), "already over"),
        (("A", "2026-11-01", 0, "Ana", "4826"), "length"),
        (("A", "2026-11-01", 30, "Ana", "1234"), "straight run"),
    ):
        with pytest.raises(ValueError, match=words):
            v.setup_mission(*args)
    assert not Vigil.mission_exists() and v.mode == "demo"


def test_mission_follows_the_calendar(run):
    v, _ = run
    info = v.mission_info()
    assert v.mode == "live" and info["day"] == 15 and info["length_days"] == 30 and info["demo_pin"] is None
    assert [w.id for w in v.store.crew] == ["ana", "priya", "lena"]  # Mission Control is not crew


def test_real_readings_raise_a_real_alert(run):
    v, _ = run
    home = v.request(LENA, "astronaut", {})
    heart = next(s for s in home["systems"] if s["id"] == "heart")
    assert not home["learning"] and heart["status"] != "green"
    assert any(a["system"] == "heart" and a["level"] >= 2 for a in home["alerts"])


def test_medical_officer_is_told_but_sees_no_numbers(run):
    v, _ = run
    titles = [n["title"] for n in v.request(MO, "notices", {})["notices"]]
    assert any("Lena Novak has a Level" in t for t in titles)
    card = next(c for c in v.request(MO, "crew_view", {})["crew"] if c["id"] == "lena")
    assert "shared_values" not in card


def test_bad_values_save_nothing(run):
    v, _ = run
    before = len(v.request(LENA, "entries", {})["entries"])
    out = v.request(LENA, "log_readings", {"values": {"resting_hr": 61, "spo2": 120}})
    assert out["saved"] == 0 and "spo2" in out["errors"] and "resting_hr" not in out["errors"]
    assert len(v.request(LENA, "entries", {})["entries"]) == before
    assert v.request(LENA, "log_readings", {"values": {"mood": 5}})["errors"]  # check-in scales come from the check-in


def test_a_mistake_can_be_removed(run):
    v, _ = run
    v.request(LENA, "log_readings", {"values": {"spo2": 97}})
    entry = v.request(LENA, "entries", {})["entries"][0]
    assert entry["signal"] == "spo2"
    v.request(LENA, "delete_entry", {"entry": entry["id"]})
    assert all(e["id"] != entry["id"] for e in v.request(LENA, "entries", {})["entries"])
    with pytest.raises(PermissionError):
        v.request(LENA, "delete_entry", {"id": "ana", "entry": 1})


def test_import_keeps_reasons_and_cannot_repeat(run):
    v, _ = run
    config.IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    (config.IMPORT_DIR / "labs.csv").write_text(
        "date,member,signal,value\n2026-11-10,Lena Novak,CRP,1.1\n2026-11-10,LN,il-6,1.9\n"
        "2026-11-11,nobody,crp,1\n2026-11-30,lena,crp,1\n2026-11-09,lena,crp,99\n2026-11-09,lena,shoe size,9\n"
    )
    assert [f["name"] for f in v.request(MO, "import_files", {})["files"]] == ["labs.csv"]
    out = v.request(MO, "import_file", {"id": "lena", "file": "labs.csv"})
    assert out["imported"] == 2 and out["skipped"] == 4 and out["members"] == ["lena"]
    assert any("nobody" in r for r in out["reasons"]) and any("future" in r for r in out["reasons"])
    assert v.request(MO, "import_files", {})["files"] == []  # moved aside after import
    with pytest.raises(LookupError):
        v.request(MO, "import_file", {"id": "lena", "file": "../mission.db"})


def test_crew_import_only_their_own_rows(run):
    v, _ = run
    (config.IMPORT_DIR / "mine.csv").write_text("date,member,signal,value\n2026-11-14,lena,spo2,98\n2026-11-14,ana,spo2,97\n")
    out = v.request(LENA, "import_file", {"file": "mine.csv"})
    assert out["imported"] == 1 and out["members"] == ["lena"]


def test_packets_are_files_and_never_duplicated(run):
    v, _ = run
    v.live.tick(0)
    v.live.tick(0)
    names = sorted(p.name for p in config.OUTBOX_DIR.glob("*.json"))
    summaries = [n for n in names if "summary" in n]
    assert len(summaries) == len(set(summaries)) == 6  # 3 crew, days 7 and 14
    out = v.request(LENA, "call_earth", {"note": "Heart rate feels high"})
    body = json.loads(next(config.OUTBOX_DIR.glob(f"*-{out['packet_id']:06d}-call-lena.json")).read_text())
    assert body["payload"]["note"] == "Heart rate feels high" and "shared_values" not in body["payload"]
    assert not list(config.OUTBOX_DIR.glob(".*.part"))


def test_ground_knows_only_what_packets_carried(run):
    v, _ = run
    g = v.request(GROUND, "ground", {})
    assert g["live"] and {c["id"] for c in g["crew"]} == {"ana", "priya", "lena"}
    assert all(set(c["systems"]) == {"immune", "bone", "heart", "behavior"} for c in g["crew"])
    assert all(p["state"] == "in_outbox" for p in g["packets"])
    first = config.OUTBOX_DIR / g["packets"][-1]["file"]
    first.unlink()  # the comm system picked it up
    assert v.request(GROUND, "ground", {})["packets"][-1]["state"] == "picked_up"


def test_export_holds_journal_words_only_when_kept(run):
    v, _ = run
    path = v.request(LENA, "export_data", {})["path"]
    rows = list(csv.reader(open(path)))
    assert rows[0] == ["kind", "day", "item", "value", "unit", "note"]
    journals = [r for r in rows if r[2] == "journal"]
    assert journals == [["check-in", "15", "journal", "", "", "Good day"]]
    assert any(r[0] == "alert" and r[2] == "Heart" for r in rows)


def test_report_and_backup(run):
    v, _ = run
    assert "Vigil health summary" in v.request(LENA, "report", {})["html"]
    backup = v.request(BOSS, "backup", {})["path"]
    assert sqlite3.connect(backup).execute("SELECT COUNT(*) FROM members").fetchone()[0] == 4


@pytest.mark.parametrize("who, name, args", [
    (LENA, "astronaut", {"id": "ana"}),
    (LENA, "log_readings", {"id": "ana", "values": {}}),
    (LENA, "accounts_admin", {}),
    (LENA, "ground", {}),
    (MO, "astronaut", {"id": "lena"}),
    (MO, "export_data", {"id": "lena"}),
    (BOSS, "astronaut", {"id": "lena"}),
    (BOSS, "report", {"id": "lena"}),
    (GROUND, "astronaut", {"id": "lena"}),
    (GROUND, "crew_view", {}),
    (BOSS, "timeline", {}),
    (BOSS, "demo_start", {}),
    (None, "astronaut", {}),
])
def test_access_rules(run, who, name, args):
    v, _ = run
    with pytest.raises(PermissionError):
        v.request(who, name, dict(args))


def test_medical_officer_may_enter_lab_results_but_sees_only_their_own_entries(run):
    v, _ = run
    assert v.request(MO, "log_readings", {"id": "lena", "values": {"crp": 1.3}})["saved"] == 1
    seen = v.request(MO, "entries", {"id": "lena"})["entries"]
    assert seen and all(e["entered_by"] == "priya" for e in seen)
    form = v.request(MO, "log_form", {"id": "lena"})
    assert form["for_someone_else"] and all(s["today"] is None and s["last"] is None for g in form["groups"] for s in g["signals"])
    lenas_own = v.request(LENA, "entries", {})["entries"][-1]
    with pytest.raises(PermissionError):
        v.request(MO, "delete_entry", {"id": "lena", "entry": lenas_own["id"]})


def test_audit_trail_has_no_secrets(run):
    v, _ = run
    events = v.request(BOSS, "audit_log", {})["events"]
    actions = {e["action"] for e in events}
    assert {"mission_created", "member_added", "readings_logged", "readings_imported", "data_exported", "backup_made"} <= actions
    text = json.dumps(events)
    assert "4826" not in text and "Good day" not in text and "Heart rate feels high" not in text


def test_reopening_finds_the_same_mission(run):
    v, today = run
    again = Vigil(mode="live", today=lambda: today[0])
    assert again.mission_info()["name"] == "Analog 1" and again.store.days_with_readings("lena") == v.store.days_with_readings("lena")


def test_archive_keeps_the_file_and_returns_to_demo(tmp_path, monkeypatch):
    point_at(monkeypatch, tmp_path)
    v = new_mission([date(2026, 11, 3)])
    with pytest.raises(ValueError):
        v.request(BOSS, "archive_mission", {})
    out = v.request(BOSS, "archive_mission", {"confirm": True})
    assert v.mode == "demo" and not Vigil.mission_exists()
    assert sqlite3.connect(out["archived_to"]).execute("SELECT value FROM settings WHERE key = 'name'").fetchone()[0] == '"Analog 1"'
