"""The rule for when to act alone, when to tell the crew, and when to call Earth."""

from dataclasses import dataclass

from ..config import Config


@dataclass(frozen=True)
class Facts:
    system: str
    flagged: int
    longest_drift_days: int
    hard_limit: str | None = None
    days_since_level2: int | None = None
    score_rise_since_level2: float = 0.0
    radiation_near_limit: bool = False


def days_text(n: int) -> str:
    return f"{n} day" if n == 1 else f"{n} days"


def decide(f: Facts, cfg: Config) -> tuple[int, str]:
    """Return the escalation level, 0 to 3, and the reason in plain words."""
    e = cfg["escalation"]
    if f.hard_limit:
        return 3, f"Escalated to Level 3 because {f.hard_limit} crossed a hard limit."
    if f.radiation_near_limit:
        return 3, "Escalated to Level 3 because radiation is near a limit."
    if (
        f.days_since_level2 is not None
        and f.days_since_level2 >= e["l3_worsen_after_days"]
        and f.score_rise_since_level2 >= e["l3_worsen_delta"]
    ):
        return 3, f"Escalated to Level 3 because drift kept getting worse {days_text(f.days_since_level2)} after Level 2."
    span = days_text(f.longest_drift_days)
    if f.flagged >= e["l2_min_signals"]:
        return 2, f"Escalated to Level 2 because {f.flagged} {f.system} signals drifted for {span}."
    if f.longest_drift_days >= e["l2_long_drift_days"]:
        return 2, f"Escalated to Level 2 because a {f.system} signal drifted for {span}."
    if f.flagged == 2 and f.longest_drift_days >= e["l1_two_signal_days"]:
        return 2, f"Escalated to Level 2 because 2 {f.system} signals drifted for {span}."
    if f.flagged >= 1:
        noun = "signal" if f.flagged == 1 else "signals"
        return 1, f"Level 1 because {f.flagged} {f.system} {noun} drifted for {span}."
    return 0, "No drift."
