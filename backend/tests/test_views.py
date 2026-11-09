import sqlite3

import pytest
from app import config
from app.views import Vigil

vigil = Vigil()
store, live = vigil.store, vigil.live


@pytest.fixture(autouse=True)
def clean():
    store.reset_interactive()
    live.stop_demo()
    live.queue = live._new_queue()
    live.packeted = set()
    live.set_day(45, 0)
    yield


def first_alert(who="eng"):
    for day in range(11, 180):
        data = vigil.astronaut(who, day=day)
        if data["alerts"]:
            return day, data["alerts"][0]
    raise AssertionError("no alert")


def test_crew_lists_everyone():
    assert len(vigil.crew()["crew"]) == 5


def test_astronaut_home_payload():
    d = vigil.astronaut("cmdr", day=30)
    assert [s["id"] for s in d["systems"]] == ["immune", "bone", "heart", "behavior"]
    assert len(d["systems"][0]["trend"]) == 30
    assert "confidence" in d["systems"][0] and d["radiation"]["limit_msv"] == 600


def test_unknown_astronaut_is_rejected():
    with pytest.raises(LookupError):
        vigil.astronaut("nobody")


def test_system_detail_has_series_and_band():
    sig = vigil.system_detail("plt", "behavior", day=60)["signals"][0]
    assert len(sig["days"]) == len(sig["values"]) == len(sig["low"]) == 60
    assert sig["low"][0] is None and sig["low"][-1] is not None


def test_unknown_system_is_rejected():
    with pytest.raises(LookupError):
        vigil.system_detail("plt", "spleen")


def visible(who, day):
    return [a["id"] for a in vigil.astronaut(who, day=day)["alerts"]]


def test_alert_detail_and_snooze():
    day, alert = first_alert()
    live.set_day(day, 0)
    detail = vigil.alert_detail("eng", alert["id"])
    assert detail["charts"] and detail["alert"]["why"]["signals"]
    vigil.alert_action("eng", alert["id"], "snooze")
    assert alert["id"] not in visible("eng", day)


def test_done_hides_until_level_rises():
    day, alert = first_alert()
    live.set_day(day, 0)
    vigil.alert_action("eng", alert["id"], "done")
    assert alert["id"] not in visible("eng", day)


def test_undo_brings_the_alert_back():
    day, alert = first_alert()
    live.set_day(day, 0)
    vigil.alert_action("eng", alert["id"], "done")
    vigil.undo_alert_action(alert["id"])
    assert alert["id"] in visible("eng", day)


def test_undo_survives_a_restart_of_the_store():
    day, alert = first_alert()
    live.set_day(day, 0)
    vigil.alert_action("eng", alert["id"], "snooze")
    vigil.undo_alert_action(alert["id"])
    store.rebuild()
    assert alert["id"] in visible("eng", day)


def test_escalate_raises_level_and_sends_level3_packet():
    day, alert = first_alert()
    live.set_day(day, 0)
    out = vigil.alert_action("eng", alert["id"], "escalate")
    assert out["alert"]["level"] == alert["level"] + 1
    while out["alert"]["level"] < 3:
        out = vigil.alert_action("eng", alert["id"], "escalate")
    assert any(p["kind"] == "level3" for p in vigil.ground()["packets"])


def test_bad_action_is_rejected():
    with pytest.raises(ValueError):
        vigil.alert_action("eng", "x", "explode")


def test_missing_alert_is_rejected():
    with pytest.raises(LookupError):
        vigil.alert_detail("eng", "eng-heart-999")


CHECKIN = {"astronaut": "mo", "mood": 2, "sleep_quality": 3, "energy": 3, "stress": 9, "symptoms": 1}


def test_checkin_stores_score_but_not_text_by_default():
    out = vigil.checkin(**CHECKIN, journal="I feel lonely and tired")
    assert out["journal_score"] < 0 and out["text_kept"] is False
    with sqlite3.connect(config.DB_PATH) as con:
        assert con.execute("SELECT journal_text FROM checkins").fetchone()[0] is None


def test_checkin_keeps_text_only_when_asked():
    vigil.checkin(**CHECKIN, journal="All good", keep_text=True)
    with sqlite3.connect(config.DB_PATH) as con:
        assert con.execute("SELECT journal_text FROM checkins").fetchone()[0] == "All good"


def test_checkin_feeds_the_engine():
    vigil.checkin(**CHECKIN)
    assert vigil.system_detail("mo", "behavior", day=45)["signals"][2]["values"][-1] == 2


def test_checkin_validates_range():
    with pytest.raises(ValueError):
        vigil.checkin(**(CHECKIN | {"mood": 11}))


def test_radiation_view():
    d = vigil.radiation("eng", day=120)
    assert d["storm"]["phase"] == "active" and d["storm"]["shelter_dose_msv"] < d["storm"]["unsheltered_dose_msv"]
    assert d["projected_total_msv"] > d["career_dose_msv"]


def test_sensors_report_real_gaps():
    series = store.mission.series["mo"]
    day = next(i + 1 for i, v in enumerate(series["spo2"]) if v != v)
    finger = next(s for s in vigil.sensors("mo", day=day)["sensors"] if s["name"] == "Finger sensor")
    assert not finger["connected"] and finger["missing"] == ["Blood oxygen"]
    assert 0 < finger["battery"] <= 100


def test_crew_view_has_no_raw_values():
    text = str(vigil.crew_view(day=155))
    assert "'message'" not in text and "'why'" not in text and "shared_values" not in text


def test_crew_summary_counts_active_alerts():
    assert "need attention" in vigil.crew_view(day=120)["summary"]


def test_ground_view_shows_level3_after_storm():
    assert vigil.ground(day=120)["level3"]


def test_share_toggle_reveals_values_to_crew():
    vigil.set_share("cmdr", share_crew=True)
    cards = {c["id"]: c for c in vigil.crew_view(day=30)["crew"]}
    assert "shared_values" in cards["cmdr"] and "shared_values" not in cards["plt"]


def test_link_loss_holds_packets():
    vigil.set_link(False)
    vigil.call_earth("cmdr")
    assert vigil.ground()["packets"][0]["state"] == "queued"
    vigil.set_link(True)
    assert vigil.ground()["packets"][0]["state"] != "queued"


def test_earth_decision_matches_level():
    assert vigil.earth_decision("eng", day=120)["decision"] == "earth"
    assert vigil.earth_decision("ctl", day=5)["decision"] == "none"


def test_timeline_is_compact_and_complete():
    t = vigil.timeline()
    assert len(t["crew"][0]["status"]["heart"]) == 180 and len(t["crew"][0]["status"]["radiation"]) == 180 and len(t["events"]) == 4


def test_clock_set_and_run():
    assert vigil.set_clock(day=77)["day"] == 77


def test_explainer_finds_same_heart_rate_real_day():
    a, b = vigil.explainer()["people"]
    assert a["verdict"] == "alert" and b["verdict"] == "normal"
    assert abs(a["value"] - b["value"]) <= 1
    assert a["median"] != b["median"]


def test_about_marks_everything_unverified():
    a = vigil.about()
    assert a["must_verify_count"] > 20 and all(s["status"] == "to verify" for s in a["sources"])


def test_results_are_available():
    assert vigil.results()["available"]


@pytest.mark.parametrize("values", [
    {"nope": 1}, {"detector": {"z_limit": "high"}}, {"detector": {"z_limit": -1}}, {"disabled_signals": ["wings"]},
])
def test_admin_rejects_unknown_and_bad_values(values):
    with pytest.raises(ValueError):
        vigil.put_config(values)


def test_admin_edit_then_restore():
    vigil.put_config({"status": {"yellow": 25}, "disabled_signals": ["hrv"]})
    assert store.cfg["status"]["yellow"] == 25
    assert "Starting values" in config.THRESHOLDS_PATH.read_text()
    assert "hrv" not in store.runs["cmdr"].signals
    vigil.reset_config()
    assert "hrv" in store.runs["cmdr"].signals


def test_demo_director_runs_in_order_and_ends():
    live.start_demo(0.0)
    assert live.snapshot(0.0)["demo"]["active"] and live.day == 1
    routes = []
    t = 0.0
    while live.demo_view()["active"]:
        t += 0.5
        view = live.snapshot(t)["demo"]
        if view.get("holding"):
            routes.append(view["route"])
        assert t < 400
    assert live.demo_view()["finished"]
    assert routes[0] == "/" and "/radiation" in routes and "/explainer" in routes and routes[-1] == "/results"
    assert 90 <= t <= 150  # about 2 minutes


def test_demo_next_beat_and_stop():
    live.start_demo(0.0)
    live.next_beat(0.0)
    assert live.demo_view()["holding"]
    live.next_beat(0.0)
    assert live.demo_view()["index"] == 1
    live.stop_demo()
    assert not live.demo_view()["active"]


def test_scrubbing_makes_no_packets():
    live.set_day(150, 0)
    live.set_day(10, 0)
    assert vigil.ground()["packets"] == []


def test_running_clock_makes_level3_packets_once():
    live.set_day(118, 0.0)
    live.running = True
    live.days_per_second = 1.0
    live.last_time = 0.0
    live.snapshot(4.0)
    live.running = False
    storm = [p for p in live.queue.packets if p.kind == "level3" and p.payload["system"] == "Radiation"]
    assert len(storm) == 5  # one per person, across both storm days


def test_demo_caption_claim_about_population_limit_is_true():
    from app.live import _first_alert
    from app.signals import BY_ID

    from scripts.evaluate_detector import fixed_limit

    alert = _first_alert(store, "heart_drift")
    value = store.mission.series["cmdr"]["resting_hr"][alert["day"] - 1]
    assert value < fixed_limit(BY_ID["resting_hr"], 2.0)
