import copy
import math
import re

import pytest
from app import config
from app.engine.alerts import DISCLAIMER, action_text, change_text, write_alert
from app.engine.baseline import compute_baseline, robust_stats, window_sizes
from app.engine.checkin import score_text
from app.engine.drift import SignalDay, SignalTracker, combine, cusum_step, ewma_limit, ewma_step
from app.engine.escalation import Facts, decide
from app.engine.fusion import drift_score, evidence
from app.engine.pipeline import run_astronaut
from app.engine.risk import signal_confidence, status_for
from app.signals import BY_ID
from app.sim.generator import CREW, generate_mission

CFG = config.load_config()
HR = BY_ID["resting_hr"]
NAN = float("nan")


def tracker(method="vote"):
    return SignalTracker(HR, CFG, method)


# Baseline math

def test_robust_stats_ignores_an_outlier():
    median, sd = robust_stats([60, 61, 62, 63, 64, 200])
    assert median == 62.5
    assert sd < 5


def test_baseline_handles_missing_days():
    with_gaps = compute_baseline([60, NAN, 62, NAN, 61, 63, 60, 62, 61, 63, 62, 60], HR, CFG)
    assert with_gaps.n_obs == 10
    assert not with_gaps.learning
    assert 60 <= with_gaps.median <= 63


def test_baseline_learning_until_enough_days():
    assert compute_baseline([60.0] * 9, HR, CFG).learning
    assert not compute_baseline([60.0] * 10, HR, CFG).learning


def test_baseline_empty_is_learning():
    assert compute_baseline([NAN, NAN], HR, CFG).learning


def test_sigma_never_below_floor():
    assert compute_baseline([60.0] * 20, HR, CFG).sigma == pytest.approx(CFG["baseline"]["sigma_floor"] * HR.noise)


def test_sparse_signals_use_fewer_readings_to_learn():
    assert window_sizes(BY_ID["crp"], CFG)[2] == CFG["baseline"]["min_observations"]


# Detectors on known series

def test_ewma_step_and_limit():
    assert ewma_step(0, 4, 0.25) == 1.0
    assert ewma_limit(0.25, 3) == pytest.approx(3 * math.sqrt(0.25 / 1.75))


def test_cusum_accumulates_and_resets_at_zero():
    assert cusum_step(0, 2, 0.5) == 1.5
    assert cusum_step(1, -5, 0.5) == 0


def test_vote_needs_two_of_three():
    assert combine({"z": True, "ewma": True, "cusum": False}, "vote", 2)
    assert not combine({"z": True, "ewma": False, "cusum": False}, "vote", 2)
    assert combine({"z": True, "ewma": False, "cusum": False}, "z", 2)


def steady(n=30):
    return [60.0 + (i % 3 - 1) * 1.5 for i in range(n)]


@pytest.mark.parametrize("method", ["z", "ewma", "cusum", "vote"])
def test_each_method_stays_quiet_on_a_steady_series(method):
    t = tracker(method)
    assert not any(t.update(v).flagged for v in steady(60))


@pytest.mark.parametrize("method", ["z", "ewma", "cusum", "vote"])
def test_each_method_catches_a_large_step(method):
    t = tracker(method)
    for v in steady():
        t.update(v)
    assert any(t.update(75.0).flagged for _ in range(10))


def test_never_flags_during_learning():
    t = tracker()
    assert not any(t.update(v).flagged for v in [60, 90, 120, 60, 110, 95, 130, 80, 70])


def test_flagged_values_stay_out_of_the_baseline():
    t = tracker()
    for v in steady():
        t.update(v)
    before = len(t.history)
    for _ in range(10):
        day = t.update(75.0)
    assert day.flagged
    assert len(t.history) <= before + 1
    assert day.median < 62


def test_missing_reading_carries_state():
    t = tracker()
    for v in steady():
        t.update(v)
    for _ in range(8):
        t.update(75.0)
    state = t.update(NAN)
    assert state.flagged and math.isnan(state.value) and state.last_value == 75.0


def test_good_direction_is_not_flagged():
    t = tracker()
    for v in steady():
        t.update(v)
    assert not any(t.update(45.0).flagged for _ in range(10))


# Fusion and risk

def test_evidence_is_zero_for_noise_and_one_at_limit():
    assert evidence(0.1, 1.0, False, CFG) == 0
    assert evidence(1.0, 1.0, False, CFG) == pytest.approx(1.0)


def test_evidence_is_capped():
    assert evidence(99, 1.0, True, CFG) == CFG["fusion"]["evidence_cap"]


def test_three_small_shifts_beat_one_of_the_same_total():
    assert drift_score([0.6, 0.6, 0.6, 0, 0, 0], CFG) > drift_score([1.8, 0, 0, 0, 0, 0], CFG)


def test_score_is_zero_with_no_evidence_and_bounded():
    assert drift_score([0, 0], CFG) == 0
    assert drift_score([3] * 20, CFG) <= 100


YELLOW, RED = CFG["status"]["yellow"], CFG["status"]["red"]


@pytest.mark.parametrize("score,level,expected", [
    (YELLOW - 1, 0, "green"), (YELLOW, 0, "yellow"), (RED, 0, "red"), (10, 2, "yellow"), (10, 3, "red"),
])
def test_status(score, level, expected):
    assert status_for(score, level, CFG) == expected


def test_confidence_falls_with_missing_data_and_young_baseline():
    full = signal_confidence(14, 14, 30, 10)
    assert full == 1.0
    assert signal_confidence(7, 14, 30, 10) < full
    assert signal_confidence(14, 14, 10, 10) < full


# Escalation boundaries

E = CFG["escalation"]


def level(**kw):
    return decide(Facts("heart", **kw), CFG)[0]


def test_no_flags_is_level_0():
    assert level(flagged=0, longest_drift_days=0) == 0


def test_one_signal_short_is_level_1():
    assert level(flagged=1, longest_drift_days=E["l2_long_drift_days"] - 1) == 1


def test_one_signal_at_long_drift_is_level_2():
    assert level(flagged=1, longest_drift_days=E["l2_long_drift_days"]) == 2


def test_two_signals_short_is_level_1():
    assert level(flagged=2, longest_drift_days=E["l1_two_signal_days"] - 1) == 1


def test_two_signals_at_three_days_is_level_2():
    assert level(flagged=2, longest_drift_days=E["l1_two_signal_days"]) == 2


def test_three_signals_is_level_2_on_day_one():
    assert level(flagged=E["l2_min_signals"], longest_drift_days=1) == 2


def test_hard_limit_is_level_3():
    assert level(flagged=1, longest_drift_days=1, hard_limit="blood oxygen") == 3


def test_radiation_near_limit_is_level_3():
    assert level(flagged=0, longest_drift_days=0, radiation_near_limit=True) == 3


def test_worsening_needs_both_time_and_size():
    delta = E["l3_worsen_delta"]
    wait = E["l3_worsen_after_days"]
    assert level(flagged=3, longest_drift_days=6, days_since_level2=wait, score_rise_since_level2=delta) == 3
    assert level(flagged=3, longest_drift_days=6, days_since_level2=wait - 1, score_rise_since_level2=delta) == 2
    assert level(flagged=3, longest_drift_days=6, days_since_level2=wait, score_rise_since_level2=delta - 1) == 2


def test_reason_is_plain_words():
    assert decide(Facts("heart", flagged=3, longest_drift_days=4), CFG)[1] == (
        "Escalated to Level 2 because 3 heart signals drifted for 4 days."
    )


# Alert text

def sample_day(value, drift_days=4):
    return SignalDay(value, value, 60.0, 2.0, 60.0, False, 2.0, ("ewma", "cusum"), True, drift_days, 1.5)


@pytest.mark.parametrize("level_", [1, 2, 3])
def test_alert_has_no_empty_fields_or_placeholders(level_):
    flagged = [(BY_ID["resting_hr"], sample_day(68.0)), (BY_ID["hrv"], sample_day(50.0))]
    alert = write_alert("cmdr", "heart", 150, 154, level_, "A reason.", flagged, 55)
    assert all(v not in ("", None) for v in alert.values())
    assert not re.search(r"[{}]|None|nan", alert["message"] + alert["action"])
    assert alert["disclaimer"] == DISCLAIMER and "diagnos" in DISCLAIMER
    row = alert["why"]["signals"][0]
    assert row["days_of_drift"] == 4 and row["current"] == 68.0 and row["rule"]


def test_message_states_size_and_time():
    alert = write_alert("cmdr", "heart", 150, 154, 1, "Reason.", [(BY_ID["resting_hr"], sample_day(68.0))], 30)
    assert alert["message"].startswith("Resting heart rate rose 8 bpm over 4 days.")


def test_singular_unit_reads_correctly():
    day = SignalDay(1.0, 1.0, 0.0, 0.5, 0.0, False, 2.0, ("ewma",), True, 2, 1.5)
    assert change_text(BY_ID["symptoms"], day) == "rose 1 point"


def test_one_action_changes_with_level():
    assert "Medical Officer" in action_text(2, "heart", "breathing")
    assert "priority packet" in action_text(3, "heart", "breathing")


def test_journal_scoring():
    assert score_text("I feel great and rested, happy today") > 0.5
    assert score_text("tired, lonely and worried") < -0.5
    assert score_text("not good") < 0
    assert score_text("the pump was serviced") == 0
    assert score_text("") == 0


# Whole pipeline

@pytest.fixture(scope="module")
def mission():
    return generate_mission(42)


def by_id(who):
    return next(c for c in CREW if c.id == who)


def test_every_day_has_every_system(mission):
    run = run_astronaut(by_id("mo"), mission, CFG)
    assert all(len(days) == 180 for days in run.systems.values())
    assert len(run.alerts) == 180


def test_no_alerts_while_learning(mission):
    run = run_astronaut(by_id("cmdr"), mission, CFG)
    assert all(not day for day in run.alerts[:10])
    assert run.systems["heart"][3]["learning"] and not run.systems["heart"][30]["learning"]


def test_planted_heart_event_is_flagged_after_onset(mission):
    run = run_astronaut(by_id("cmdr"), mission, CFG)
    assert any(a["system"] == "heart" for day in run.alerts[150:165] for a in day)


def test_storm_is_level_3_with_shelter_action(mission):
    run = run_astronaut(by_id("eng"), mission, CFG)
    storm = [a for a in run.alerts[119] if a["system"] == "radiation"][0]
    assert storm["level"] == 3 and "shelter" in storm["action"]


def test_near_limit_alert_fires_when_limit_is_lowered(mission):
    tight = copy.deepcopy(CFG)
    tight["radiation"]["career_limit_msv"] = 300
    run = run_astronaut(by_id("cmdr"), mission, tight)
    assert any(a["system"] == "radiation" and "near a limit" in a["level_reason"] for a in run.alerts[60])


def test_disabled_signal_is_skipped(mission):
    off = copy.deepcopy(CFG)
    off["disabled_signals"] = ["hrv"]
    assert "hrv" not in run_astronaut(by_id("plt"), mission, off).signals
