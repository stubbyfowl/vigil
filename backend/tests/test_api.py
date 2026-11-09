import json
import sqlite3

import pytest
from app import config
from app.main import app
from app.routes.deps import live, store
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean():
    store.reset_interactive()
    live.stop_demo()
    live.queue = live._new_queue()
    live.packeted = set()
    live.set_day(45, 0)
    yield


def get(path):
    r = client.get(path)
    assert r.status_code == 200, r.text
    return r.json()


def post(path, body=None):
    r = client.post(path, json=body or {})
    assert r.status_code == 200, r.text
    return r.json()


def first_alert(who="eng"):
    for day in range(11, 180):
        data = get(f"/api/astronaut/{who}?day={day}")
        if data["alerts"]:
            return day, data["alerts"][0]
    raise AssertionError("no alert")


def test_crew_lists_everyone():
    assert len(get("/api/crew")["crew"]) == 5


def test_astronaut_home_payload():
    d = get("/api/astronaut/cmdr?day=30")
    assert [s["id"] for s in d["systems"]] == ["immune", "bone", "heart", "behavior"]
    assert len(d["systems"][0]["trend"]) == 30
    assert "confidence" in d["systems"][0] and d["radiation"]["limit_msv"] == 600


def test_unknown_astronaut_is_404():
    assert client.get("/api/astronaut/nobody").status_code == 404


def test_system_detail_has_series_and_band():
    d = get("/api/astronaut/plt/system/behavior?day=60")
    sig = d["signals"][0]
    assert len(sig["days"]) == len(sig["values"]) == len(sig["low"]) == 60
    assert sig["low"][0] is None and sig["low"][-1] is not None


def test_unknown_system_is_404():
    assert client.get("/api/astronaut/plt/system/spleen").status_code == 404


def test_alert_detail_and_actions():
    day, alert = first_alert()
    live.set_day(day, 0)
    detail = get(f"/api/astronaut/eng/alert/{alert['id']}")
    assert detail["charts"] and detail["alert"]["why"]["signals"]

    post(f"/api/astronaut/eng/alert/{alert['id']}/action", {"action": "snooze"})
    assert alert["id"] not in [a["id"] for a in get(f"/api/astronaut/eng?day={day}")["alerts"]]


def test_done_hides_until_level_rises():
    day, alert = first_alert()
    live.set_day(day, 0)
    post(f"/api/astronaut/eng/alert/{alert['id']}/action", {"action": "done"})
    assert alert["id"] not in [a["id"] for a in get(f"/api/astronaut/eng?day={day}")["alerts"]]


def test_escalate_raises_level_and_sends_level3_packet():
    day, alert = first_alert()
    live.set_day(day, 0)
    out = post(f"/api/astronaut/eng/alert/{alert['id']}/action", {"action": "escalate"})
    assert out["alert"]["level"] == alert["level"] + 1
    while out["alert"]["level"] < 3:
        out = post(f"/api/astronaut/eng/alert/{alert['id']}/action", {"action": "escalate"})
    assert any(p["kind"] == "level3" for p in get("/api/ground")["packets"])


def test_bad_action_is_rejected():
    assert client.post("/api/astronaut/eng/alert/x/action", json={"action": "explode"}).status_code == 422


def test_missing_alert_is_404():
    assert client.get("/api/astronaut/eng/alert/eng-heart-999").status_code == 404


CHECKIN = {"astronaut": "mo", "mood": 2, "sleep_quality": 3, "energy": 3, "stress": 9, "symptoms": 1}


def test_checkin_stores_score_but_not_text_by_default():
    out = post("/api/checkin", CHECKIN | {"journal": "I feel lonely and tired"})
    assert out["journal_score"] < 0 and out["text_kept"] is False
    with sqlite3.connect(config.DB_PATH) as con:
        assert con.execute("SELECT journal_text FROM checkins").fetchone()[0] is None


def test_checkin_keeps_text_only_when_asked():
    post("/api/checkin", CHECKIN | {"journal": "All good", "keep_text": True})
    with sqlite3.connect(config.DB_PATH) as con:
        assert con.execute("SELECT journal_text FROM checkins").fetchone()[0] == "All good"


def test_checkin_feeds_the_engine():
    post("/api/checkin", CHECKIN)
    assert get("/api/astronaut/mo/system/behavior?day=45")["signals"][2]["values"][-1] == 2


def test_checkin_validates_range():
    assert client.post("/api/checkin", json=CHECKIN | {"mood": 11}).status_code == 422


def test_radiation_view():
    d = get("/api/astronaut/eng/radiation?day=120")
    assert d["storm"]["phase"] == "active" and d["storm"]["shelter_dose_msv"] < d["storm"]["unsheltered_dose_msv"]
    assert d["projected_total_msv"] > d["career_dose_msv"]


def test_crew_view_has_no_raw_values():
    text = json.dumps(get("/api/crew-view?day=155"))
    assert '"message"' not in text and '"why"' not in text and "shared_values" not in text


def test_ground_view_shows_level3_after_storm():
    assert get("/api/ground?day=120")["level3"]


def test_share_toggle_reveals_values_to_crew():
    post("/api/astronaut/cmdr/share", {"share_crew": True})
    cards = {c["id"]: c for c in get("/api/crew-view?day=30")["crew"]}
    assert "shared_values" in cards["cmdr"] and "shared_values" not in cards["plt"]


def test_link_loss_holds_packets():
    post("/api/link", {"up": False})
    post("/api/call-earth", {"astronaut": "cmdr"})
    assert get("/api/ground")["packets"][0]["state"] == "queued"
    post("/api/link", {"up": True})
    assert get("/api/ground")["packets"][0]["state"] != "queued"


def test_earth_decision_matches_level():
    assert get("/api/astronaut/eng/earth?day=120")["decision"] == "earth"
    assert get("/api/astronaut/ctl/earth?day=5")["decision"] == "none"


def test_timeline_is_compact_and_complete():
    t = get("/api/timeline")
    assert len(t["crew"][0]["status"]["heart"]) == 180 and len(t["events"]) == 4


def test_clock_set_and_run():
    assert post("/api/clock", {"day": 77})["day"] == 77
    assert client.post("/api/clock", json={"day": 0}).status_code == 422


def test_explainer_finds_same_heart_rate_real_day():
    e = get("/api/explainer")
    a, b = e["people"]
    assert a["verdict"] == "alert" and b["verdict"] == "normal"
    assert abs(a["value"] - b["value"]) <= 1
    assert a["median"] != b["median"]


def test_about_marks_everything_unverified():
    a = get("/api/about")
    assert a["must_verify_count"] > 20 and all(s["status"] == "to verify" for s in a["sources"])


def test_results_endpoint():
    assert "available" in get("/api/results")


def test_sim_stream_emits_requested_days():
    with client.stream("GET", "/api/sim/stream?start=3&end=4&speed=60") as r:
        lines = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert [x["day"] for x in lines] == [3, 4]


def test_admin_rejects_unknown_and_bad_values():
    assert client.put("/api/admin/config", json={"values": {"nope": 1}}).status_code == 422
    assert client.put("/api/admin/config", json={"values": {"detector": {"z_limit": "high"}}}).status_code == 422
    assert client.put("/api/admin/config", json={"values": {"detector": {"z_limit": -1}}}).status_code == 422
    assert client.put("/api/admin/config", json={"values": {"disabled_signals": ["wings"]}}).status_code == 422


def test_admin_edit_then_restore():
    r = client.put("/api/admin/config", json={"values": {"status": {"yellow": 25}, "disabled_signals": ["hrv"]}})
    assert r.status_code == 200 and store.cfg["status"]["yellow"] == 25
    assert "Starting values" in config.THRESHOLDS_PATH.read_text()
    assert "hrv" not in store.runs["cmdr"].signals
    post("/api/admin/reset")
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
    assert get("/api/ground")["packets"] == []


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
