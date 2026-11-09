import numpy as np
from app.signals import DRIFT_SIGNALS, SIGNALS
from app.sim.generator import CREW, generate_mission


def test_same_seed_same_mission():
    a, b = generate_mission(7), generate_mission(7)
    for who in a.series:
        for sig in a.series[who]:
            assert np.array_equal(a.series[who][sig], b.series[who][sig], equal_nan=True)


def test_different_seed_differs():
    a, b = generate_mission(1), generate_mission(2)
    assert not np.array_equal(a.series["cmdr"]["hrv"], b.series["cmdr"]["hrv"], equal_nan=True)


def test_every_signal_exists_within_range():
    m = generate_mission(3)
    assert len(m.series) == len(CREW)
    for who in m.series:
        for sig in SIGNALS:
            values = m.series[who][sig.id]
            assert len(values) == 180
            assert np.nanmin(values) >= sig.low and np.nanmax(values) <= sig.high


def test_about_three_percent_missing_on_daily_signals():
    m = generate_mission(4)
    daily = [s.id for s in DRIFT_SIGNALS if s.cadence == 1]
    rate = np.mean([np.isnan(m.series["mo"][s]).mean() for s in daily])
    assert 0.015 < rate < 0.05


def test_weekly_signals_are_sparse():
    m = generate_mission(5)
    assert 22 <= np.sum(~np.isnan(m.series["eng"]["crp"])) <= 26


def test_personal_baselines_differ():
    m = generate_mission(6)
    medians = [np.nanmedian(m.series[w.id]["resting_hr"][:30]) for w in CREW]
    assert max(medians) - min(medians) > 5


def test_planted_events_saved_and_visible():
    m = generate_mission(8)
    assert [e["day"] for e in m.ground_truth] == [40, 90, 120, 150]
    temp = m.series["eng"]["temp"]
    assert np.nanmean(temp[43:52]) - np.nanmean(temp[15:38]) > 0.2


def test_quiet_astronaut_has_no_planted_shift():
    m = generate_mission(9)
    assert all(e["astronaut"] != "ctl" for e in m.ground_truth)


def test_storm_has_warning_and_spike():
    m = generate_mission(10)
    assert m.storm is not None
    assert m.storm["onset_hour"] - m.storm["warning_hour"] == 2
    assert m.storm["end_hour"] - m.storm["onset_hour"] == 36
    free = m.hourly_free["cmdr"]
    assert free[m.storm["onset_hour"]:m.storm["end_hour"]].max() > 5 * np.median(free)
    assert m.series["cmdr"]["spe_flag"][119] == 1 and m.series["cmdr"]["spe_flag"][100] == 0


def test_shelter_reduces_measured_dose():
    m = generate_mission(11)
    s = m.storm
    assert m.hourly["mo"][s["onset_hour"] + 1:s["end_hour"]].sum() < m.hourly_free["mo"][s["onset_hour"] + 1:s["end_hour"]].sum()


def test_cumulative_dose_is_about_1_8_per_day():
    m = generate_mission(12, planted=False)
    assert 1.6 < m.series["plt"]["cum_dose"][-1] / 180 < 2.0


def test_no_events_mode():
    assert generate_mission(13, planted=False).ground_truth == []
