"""Turn flags into short plain-language alerts."""

import json
from pathlib import Path
from typing import Any

from ..signals import BY_ID, SYSTEMS, Signal
from .drift import PLAIN_NAMES, SignalDay
from .escalation import days_text

PROTOCOLS: dict[str, Any] = json.loads((Path(__file__).parent / "protocols.json").read_text())
DISCLAIMER = "Decision support, not a diagnosis."
PERCENT_SIGNALS = {"sleep_hours", "social_min", "exercise_min", "exercise_load", "hrv", "grip"}
UNIT_WORDS = {
    "%": "points", "min": "minutes", "AU": "units", "index": "points", "ratio": "points",
    "0 to 5": "points", "1 to 10": "points", "-1 to 1": "points",
}
SHORT_NAMES = {"sleep_hours": "Sleep", "ortho_rise": "Heart rate rise on standing", "journal": "Journal tone"}
WHY_MATTERS = {
    "immune": "These changes often come together when the body fights illness.",
    "heart": "These changes can mean the heart is working harder than usual.",
    "behavior": "These changes often come together under stress or isolation.",
    "bone": "Less loading can speed up bone and muscle loss in low gravity.",
}
SINGLE_SIGNAL_NOTE = "One change alone is often nothing, but it is worth a closer look."
BY_SIGNAL = {
    "ortho_rise": "hydration", "sleep_hours": "sleep_reset", "sleep_eff": "sleep_reset",
    "social_min": "social_call", "stress": "breathing", "mood": "light_exposure", "energy": "light_exposure",
    "journal": "social_call", "temp": "rest_day", "resting_hr": "breathing", "hrv": "breathing",
}
BY_SYSTEM = {"immune": "rest_day", "heart": "breathing", "behavior": "sleep_reset", "bone": "exercise_adjustment"}
RECHECK_HOURS = {1: 48, 2: 24, 3: 6}


def change_text(sig: Signal, day: SignalDay) -> str:
    """Example: 'fell 22%' or 'rose 8 bpm'."""
    delta = day.last_value - day.median
    verb = "rose" if delta >= 0 else "fell"
    if sig.id in PERCENT_SIGNALS and day.median:
        return f"{verb} {abs(delta) / abs(day.median) * 100:.0f}%"
    size = f"{abs(delta):.{min(sig.decimals, 2)}f}"
    unit = UNIT_WORDS.get(sig.unit, sig.unit)
    if size == "1" and sig.unit in UNIT_WORDS:
        unit = unit.removesuffix("s")
    return f"{verb} {size} {unit}".rstrip()


def _rule_text(day: SignalDay) -> str:
    names = [PLAIN_NAMES[m] for m in day.fired]
    if not names:
        return "Readings stayed outside this person's normal."
    joined = " and ".join(names)
    return f"{joined} crossed {'its limit' if len(names) == 1 else 'their limits'}."


def choose_protocol(system: str, top_signal: str) -> str:
    return BY_SIGNAL.get(top_signal) or BY_SYSTEM[system]


def action_text(level: int, system: str, protocol_id: str) -> str:
    """Exactly one action, chosen by escalation level."""
    if level >= 3:
        return "Send the priority packet to Earth and start the emergency checklist."
    if level == 2:
        return f"Tell the Medical Officer and run the longer {SYSTEMS[system].lower()} check."
    return f"Do the {PROTOCOLS[protocol_id]['name']} today."


def why_entry(sig: Signal, day: SignalDay) -> dict[str, Any]:
    """One row of the Why? drawer."""
    return {
        "signal": sig.id, "name": sig.name, "unit": sig.unit,
        "baseline_median": round(day.median, 2),
        "baseline_low": round(day.median - 2 * day.sigma, 2),
        "baseline_high": round(day.median + 2 * day.sigma, 2),
        "current": round(day.last_value, 2),
        "change": round(day.last_value - day.median, 2),
        "days_of_drift": day.drift_days,
        "rule": _rule_text(day),
    }


def write_alert(
    who: str, system: str, open_day: int, today: int, level: int, reason: str,
    flagged: list[tuple[Signal, SignalDay]], score: float,
) -> dict[str, Any]:
    """Build the alert. flagged must hold at least one signal, strongest first."""
    top_sig, top_day = flagged[0]
    sentences = [
        f"{SHORT_NAMES.get(top_sig.id, top_sig.name)} {change_text(top_sig, top_day)} "
        f"over {days_text(top_day.drift_days)}."
    ]
    sentences += [f"{SHORT_NAMES.get(s.id, s.name)} {change_text(s, d)}." for s, d in flagged[1:3]]
    sentences.append(WHY_MATTERS[system] if len(flagged) > 1 else SINGLE_SIGNAL_NOTE)
    protocol_id = choose_protocol(system, top_sig.id)
    action = action_text(level, system, protocol_id)
    recheck = RECHECK_HOURS[level]
    return {
        "id": f"{who}-{system}-{open_day}",
        "astronaut": who, "system": system, "system_name": SYSTEMS[system],
        "opened_day": open_day, "day": today, "level": level, "level_reason": reason,
        "message": " ".join(sentences), "action": action, "protocol": protocol_id,
        "recheck_hours": recheck, "recheck_text": f"Recheck in {recheck} hours.",
        "disclaimer": DISCLAIMER, "score": round(score),
        "why": {"signals": [why_entry(s, d) for s, d in flagged], "rule": reason},
        "top_signal": top_sig.id,
    }


def signal_name(signal_id: str) -> str:
    return BY_ID[signal_id].name
