"""The body map, NASA's five hazards, the new nutrition and cabin air readings, and the guidance for every reading."""

import json

import numpy as np
import pytest
from app import body, config, mission
from app.signals import BY_ID, DRIFT_SIGNALS, GROUP_NAMES
from app.views import Vigil

vigil = Vigil()
P = {"id": "presenter", "role": "presenter"}


def test_the_five_hazards_are_nasas_own():
    names = [h["name"] for h in body.HAZARDS]
    assert names == ["Space radiation", "Isolation and confinement", "Distance from Earth", "Gravity fields", "Hostile closed environments"]
    reached = {h for r in body.REGIONS for h in r["hazards"]}
    assert reached == {h["id"] for h in body.HAZARDS}  # every hazard reaches some part of the body


def test_every_reading_has_guidance_and_every_region_names_real_risks():
    guide = body.guide()
    for sid in [s.id for s in DRIFT_SIGNALS] + ["glucose", "body_mass", "co2", "fiber", "processed", "daily_dose"]:
        assert {"measure", "why", "act"} <= set(guide[sid]), sid
    risks = json.loads((config.DATA_DIR / "sources.json").read_text())
    catalog = next(s for s in risks["sources"] if s["id"] == "hrp_risks")["gives"]
    for region in body.REGIONS:
        for risk in region["risks"]:
            assert risk.removeprefix("Risk of ").lower() in catalog.lower(), risk


@pytest.mark.parametrize("value, status, word", [
    (53, "red", "Severe low"), (69, "red", "Low"), (70, "green", "Normal"), (99, "green", "Normal"),
    (100, "yellow", "Above normal"), (125, "yellow", "Above normal"), (126, "red", "High"),
])
def test_blood_sugar_uses_the_cdc_ranges(value, status, word):
    assert body.reference_status("glucose", value, None)[:2] == (status, word)


def test_cabin_co2_uses_nasas_limit():
    assert body.reference_status("co2", 3.0, None)[0] == "green"
    assert body.reference_status("co2", 3.1, None)[:2] == ("red", "Above NASA's limit")


def test_body_map_covers_every_part_and_flags_the_co2_fault():
    normal = vigil.request(P, "body_map", {"id": "eng", "day": 49})
    assert [r["id"] for r in normal["regions"]] == [r["id"] for r in body.REGIONS]
    assert next(r for r in normal["regions"] if r["id"] == "immune")["status"] == "red"  # Lena's immune alert
    fault = vigil.request(P, "body_map", {"id": "eng", "day": 85})
    lungs = next(r for r in fault["regions"] if r["id"] == "lungs")
    co2 = next(x for x in lungs["readings"] if x["id"] == "co2")
    assert lungs["status"] == "red" and co2["word"] == "Above NASA's limit" and co2["guide"]["act"]


def test_co2_fault_prompts_on_home_and_new_readings_leave_old_alerts_alone():
    vigil.set_clock(day=85, running=False)
    notices = vigil.request(P, "notices", {"id": "eng"})["notices"]
    assert any("above NASA's limit" in n["title"] for n in notices)
    vigil.set_clock(day=49, running=False)
    assert vigil.astronaut("eng", day=49)["alerts"][0]["id"] == "eng-immune-46"
    assert "glucose" not in vigil.store.runs["eng"].signals and "co2" not in vigil.store.runs["eng"].signals


def test_new_readings_can_be_logged_and_imported():
    assert {"glucose", "body_mass", "co2"} <= {s.id for s in mission.LOGGABLE}
    assert GROUP_NAMES[BY_ID["glucose"].system] == "Nutrition" and GROUP_NAMES[BY_ID["co2"].system] == "Cabin air"
    assert mission._apple_value("glucose", "mmol<180.1558800000541>/L", 5.0) == pytest.approx(90.0)
    assert mission._apple_value("body_mass", "lb", 100) == pytest.approx(45.359, abs=0.01)
    assert mission.ALIASES["blood sugar"] == "glucose" and mission.ALIASES["carbon dioxide"] == "co2"


def test_demo_cabin_air_is_shared_and_crosses_the_limit_only_in_the_fault():
    s = vigil.store.mission.series
    assert np.array_equal(s["eng"]["co2"], s["cmdr"]["co2"])
    over = np.flatnonzero(s["eng"]["co2"] > 3.0) + 1
    assert set(over) <= set(range(84, 87)) and len(over) >= 1


def test_nasa_space_weather_is_offered_when_bundled():
    out = vigil.request(P, "space_weather", {})
    if (config.DATA_DIR / "space_weather" / "nasa_donki_sep.json").exists():
        assert out["available"] and out["storms"] >= 50 and len(out["recent"]) == 5
        assert sum(p["storms"] for p in out["per_year"]) == out["storms"] and out["entries"] > out["storms"]
    else:
        assert out == {"available": False}
