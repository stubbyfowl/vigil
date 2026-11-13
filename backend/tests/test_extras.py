"""Organ chat, future you, lab ticker, immune replay, heart rate album, Gut City and the narrator."""

import re
import wave
from datetime import datetime

import numpy as np
import pytest
from app import config, extras, music
from app.models import CheckIn
from app.views import Vigil

vigil = Vigil()
store = vigil.store
P = {"id": "presenter", "role": "presenter"}
ENG = {"id": "eng", "role": "crew"}
REQUESTS = ("organ_chat", "future_you", "lab_ticker", "immune_replay", "gut_city", "narration", "album")


@pytest.fixture(autouse=True)
def clean():
    store.reset_interactive()
    yield


def no_em_dash(value):
    assert chr(0x2014) not in repr(value)  # the em dash


def test_every_organ_message_names_the_reading_behind_it():
    chat = vigil.request(P, "organ_chat", {"id": "eng", "day": 49})
    assert chat["messages"] and {m["organ"] for m in chat["messages"]} <= set(extras.ORGANS)
    for m in chat["messages"]:
        assert 43 <= m["day"] <= 49 and m["why"]
        # A message that quotes a number must quote the same number as its reading.
        for number in re.findall(r"\d+\.\d+", m["text"]):
            assert number in m["why"] or m["organ"] == "immune", m
    no_em_dash(chat)


def test_organs_react_to_real_drift():
    # Lena's immune drift opens on day 46, so her temperature and the immune system both speak up.
    texts = [m["text"] for m in vigil.request(P, "organ_chat", {"id": "eng", "day": 49})["messages"] if m["day"] == 49]
    assert any("warm" in t for t in texts) and any("handling something" in t or "marathon" in t for t in texts)
    quiet = extras.organ_chat(store.runs["eng"], store.mission.series["eng"], 25)
    assert not any("handling something" in m["text"] for m in quiet["messages"])


def test_brain_says_sleep_only_late_at_night():
    run, series = store.runs["eng"], store.mission.series["eng"]
    late = extras.organ_chat(run, series, 49, datetime(2026, 11, 13, 2, 0))
    noon = extras.organ_chat(run, series, 49, datetime(2026, 11, 13, 12, 0))
    assert any(m["text"] == "It's 02:00. Let's sleep!" for m in late["messages"])
    assert not any("Let's sleep" in m["text"] for m in noon["messages"])


def test_future_you_turns_grumpy_when_habits_slip():
    run = store.runs["eng"]
    series = {k: v.copy() for k, v in store.mission.series["eng"].items()}
    assert vigil.request(P, "future_you", {"id": "eng", "day": 49})["mood"] in ("chill", "okay")
    series["exercise_min"][35:49] = 20
    series["sleep_hours"][35:49] = 3.5
    series["stress"][35:49] = 9
    series["social_min"][35:49] = 5
    out = extras.future_you(run, series, 49)
    assert out["mood"] == "grumpy" and any(t["text"] == "My knees hate you." for t in out["texts"])
    assert "Not a prediction" in out["texts"][0]["why"]


def test_lab_ticker_reads_like_a_market_and_says_which_way_is_bad():
    out = vigil.request(P, "lab_ticker", {"id": "eng", "day": 49})
    crp = next(i for i in out["items"] if i["symbol"] == "CRP")
    assert crp["move"] == "up" and crp["worse"] and ("Analysts concerned" in crp["text"] or "nervous" in crp["text"])
    assert all(i["move"] in ("up", "down", "flat", "new") for i in out["items"])
    no_em_dash(out)


def test_immune_replay_follows_the_real_alert():
    out = vigil.request(P, "immune_replay", {"id": "eng", "day": 60})
    assert out["available"] and out["open_day"] == 46 and out["result"] == "Still in play"
    days = [f["day"] for f in out["frames"]]
    assert days == list(range(40, 61))
    assert all(-1 <= v <= 1 for f in out["frames"] for v in f["lanes"].values())
    assert any("opens an immune alert" in f["line"] for f in out["frames"])
    assert vigil.request(P, "immune_replay", {"id": "eng", "day": 10})["available"] is False


def test_album_maps_heart_rate_stress_and_sleep_to_music(tmp_path):
    out = vigil.request(P, "album", {"id": "cmdr", "day": 70})
    assert out["month"] == 3 and out["months"] == 3
    for t in out["tracks"]:
        assert t["style"] in ("Lo-fi", "Downtempo", "Drum and bass")
        if t["style"] == "Lo-fi":
            assert t["tempo"] == min(95, max(50, t["heart_rate"]))
        assert t["seconds"] == min(40, max(16, round(t["sleep"] * music.SECONDS_PER_SLEEP_HOUR)))
    track = out["tracks"][0]
    path = music.render(track, tmp_path / "a.wav")
    with wave.open(str(path)) as w:
        assert w.getframerate() == music.RATE and abs(w.getnframes() / music.RATE - track["seconds"]) < 0.1
    assert path.read_bytes() == music.render(track, tmp_path / "b.wav").read_bytes()  # same week, same sound


def test_album_track_is_made_once_and_reused(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "EXPORT_DIR", tmp_path)
    first = vigil.request(P, "album_track", {"id": "eng", "month": 2, "number": 1, "day": 49})["path"]
    again = vigil.request(P, "album_track", {"id": "eng", "month": 2, "number": 1, "day": 49})["path"]
    assert first == again and len(list((tmp_path / "album").glob("*.wav"))) == 1
    with pytest.raises(LookupError):
        vigil.request(P, "album_track", {"id": "eng", "month": 2, "number": 4, "day": 49})


def test_gut_city_is_built_from_the_check_in():
    series = {k: v.copy() for k, v in store.mission.series["eng"].items()}
    series["fiber"][:] = np.nan
    series["processed"][:] = np.nan
    empty = extras.gut_city(series, 49)
    assert empty["answered_days"] == 0 and empty["tiles"] == [] and empty["population"] == 0
    series["fiber"][40:43] = [5, 4, 3]
    series["processed"][43] = 4
    city = extras.gut_city(series, 49)
    assert [t["kind"] for t in city["tiles"]] == ["tower", "park", "houses"]
    assert city["tiles"][-1]["trashed"] and "raccoon gang" in city["events"][0]
    assert city["population"] == 4000 + 300


def test_food_answers_are_optional_checked_and_saved():
    with pytest.raises(ValueError):
        CheckIn("eng", 7, 6, 7, 3, 0, fiber=9)
    base = {"astronaut": "eng", "mood": 7, "sleep_quality": 6, "energy": 7, "stress": 3, "symptoms": 0}
    vigil.request(ENG, "checkin", base)
    d = vigil._day(None)
    vigil.request(ENG, "checkin", base | {"fiber": 5, "processed": 0})
    assert store.mission.series["eng"]["fiber"][d - 1] == 5 and store.mission.series["eng"]["processed"][d - 1] == 0
    store.rebuild()  # read back from the database
    assert store.mission.series["eng"]["fiber"][d - 1] == 5


def test_food_answers_never_change_the_health_engine():
    # Food has its own system, so the drift engine never scores it and the demo's readings are unchanged.
    assert "fiber" not in store.runs["eng"].signals and "processed" not in store.runs["eng"].signals
    assert vigil.astronaut("eng", day=49)["alerts"][0]["id"] == "eng-immune-46"


def test_narrator_reads_real_reminders():
    lines = vigil.request(P, "narration", {"id": "eng", "day": 49})["lines"]
    assert any("Will it remember this time?" in line for line in lines)
    assert any("check-in screen waits" in line for line in lines)
    no_em_dash(lines)


@pytest.mark.parametrize("name", REQUESTS)
def test_each_person_sees_only_their_own(name):
    assert vigil.request(ENG, name, {"day": 49})  # their own
    with pytest.raises(PermissionError):
        vigil.request(ENG, name, {"id": "cmdr", "day": 49})
    with pytest.raises(PermissionError):
        vigil.request({"id": "surgeon", "role": "ground"}, name, {"id": "eng"})
