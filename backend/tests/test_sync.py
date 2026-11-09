import json

import pytest
from app.engine.pipeline import run_astronaut
from app.sim.generator import CREW
from app.sync.privacy import crew_card, ground_card
from app.sync.queue import PRIORITY_LEVEL3, PRIORITY_NORMAL, SyncQueue

from tests.test_engine import CFG, generate_mission


def queue(delay=20.0, bandwidth=10.0):
    return SyncQueue(delay, bandwidth)


def send(q, t, priority, size=10.0, title="p"):
    return q.enqueue(t, "x", "cmdr", title, priority, size, 1, {})


def test_packet_states_follow_time():
    q = queue()
    p = send(q, 0.0, PRIORITY_NORMAL)
    assert p.state(0.5) == "sent"
    assert p.state(1.5) == "in_transit"
    assert p.state(21.5) == "received"


def test_level3_jumps_the_queue():
    q = queue()
    send(q, 0.0, PRIORITY_NORMAL, title="first")
    normal = send(q, 0.1, PRIORITY_NORMAL, title="waiting")
    urgent = send(q, 0.2, PRIORITY_LEVEL3, title="urgent")
    q.update(1.5)
    assert urgent.sent_at is not None and normal.sent_at is None


def test_lost_link_queues_then_sends():
    q = queue()
    q.set_link(False, 0.0)
    p = send(q, 0.0, PRIORITY_LEVEL3)
    q.update(100.0)
    assert p.state(100.0) == "queued"
    q.set_link(True, 200.0)
    assert p.sent_at == 200.0


def test_view_counts_down():
    q = queue()
    send(q, 0.0, PRIORITY_NORMAL)
    row = q.view(5.0)[0]
    assert row["state"] == "in_transit" and row["seconds_left"] == 16.0


@pytest.fixture(scope="module")
def run():
    return run_astronaut(next(c for c in CREW if c.id == "cmdr"), generate_mission(42), CFG)


def alerts_for(run):
    return next((d, a) for d, a in enumerate(run.alerts, start=1) if any(x["level"] >= 3 for x in a))


FORBIDDEN_KEYS = {"message", "why", "action", "journal", "journal_text", "value", "values", "current", "shared_values", "last_value"}


def keys(obj):
    if isinstance(obj, dict):
        yield from obj
        for v in obj.values():
            yield from keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys(v)


def test_crew_tier_has_no_raw_values(run):
    day, alerts = alerts_for(run)
    assert not set(keys(crew_card(run, day, alerts, False))) & FORBIDDEN_KEYS


def test_ground_tier_has_no_raw_values_but_keeps_level3(run):
    day, alerts = alerts_for(run)
    card = ground_card(run, day, alerts, False)
    assert not set(keys(card)) & FORBIDDEN_KEYS
    assert card["level3"] and card["level3"][0]["reason"]
    current = next(a for a in alerts if a["level"] >= 3)["why"]["signals"][0]["current"]
    assert f"{current}" not in json.dumps(card["level3"])


def test_raw_values_only_after_sharing(run):
    day, alerts = alerts_for(run)
    assert "shared_values" in crew_card(run, day, alerts, True)
    assert "shared_values" in ground_card(run, day, alerts, True)
