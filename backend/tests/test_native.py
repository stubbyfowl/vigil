"""The C++ tracker must give the same answer as the Python tracker, bit for bit."""

import math

import pytest
from app import config
from app.engine import drift, fast
from app.engine.drift import SignalTracker, ewma_limit
from app.signals import DRIFT_SIGNALS
from app.sim.generator import CREW, generate_mission

CFG = config.load_config()


def same(a, b):
    return a == b or (isinstance(a, float) and math.isnan(a) and math.isnan(b))


@pytest.mark.skipif(not fast.available(), reason="C++ tracker not built. Run: make native")
@pytest.mark.parametrize("seed", [42, 2000, 2007])
@pytest.mark.parametrize("method", ["z", "ewma", "cusum", "vote"])
def test_cpp_matches_python_exactly(seed, method):
    mission = generate_mission(seed)
    for who in CREW:
        for sig in DRIFT_SIGNALS:
            values = mission.series[who.id][sig.id]
            tracker = SignalTracker(sig, CFG, method)
            expected = [tracker.update(float(v)) for v in values]
            d = CFG["detector"]
            out = fast.track(sig, values, CFG, method, ewma_limit(d["ewma_lambda"], d["ewma_l"]))
            for i, want in enumerate(expected):
                for field in ("last_value", "median", "sigma", "short_median", "ewma", "evidence", "learning", "flagged", "drift_days", "fired"):
                    got = out[field][i]
                    assert same(got, getattr(want, field)), f"{who.id} {sig.id} day {i + 1} {field}: {got} != {getattr(want, field)}"


def test_python_fallback_runs_without_the_library(monkeypatch):
    monkeypatch.setattr(fast, "_lib", None)
    mission = generate_mission(5)
    states = drift.track_signal(DRIFT_SIGNALS[0], mission.series["cmdr"][DRIFT_SIGNALS[0].id], CFG)
    assert len(states) == 180 and states[-1].median == states[-1].median
