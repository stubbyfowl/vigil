"""System status and confidence."""

from ..config import Config


def status_for(score: float, level: int, cfg: Config) -> str:
    """Status comes from the score, and escalation can only raise it."""
    s = cfg["status"]
    if score >= s["red"] or level >= 3:
        return "red"
    if score >= s["yellow"] or level >= 2:
        return "yellow"
    return "green"


def signal_confidence(observed_recent: int, expected_recent: int, n_obs: int, needed: int) -> float:
    """Confidence falls when recent readings are missing or the baseline is young."""
    completeness = min(1.0, observed_recent / max(expected_recent, 1))
    maturity = min(1.0, n_obs / (2 * needed))
    return completeness * maturity
