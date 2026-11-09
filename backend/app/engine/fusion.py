"""Combine small shifts across signals into one system drift score."""

from math import exp

from ..config import Config

BROAD_EVIDENCE = 0.5  # a signal counts toward breadth at this much evidence


def evidence(ewma: float, limit: float, flagged: bool, cfg: Config) -> float:
    """Scale one signal: 0 is ordinary noise, 1 is at its control limit."""
    f = cfg["fusion"]
    raw = (ewma / limit - f["dead_zone"]) / (1 - f["dead_zone"])
    return min(max(raw, 1.0 if flagged else 0.0, 0.0), f["evidence_cap"])


def drift_score(evidences: list[float], cfg: Config) -> float:
    """Return 0 to 100. Several moving signals score more than their plain sum."""
    f = cfg["fusion"]
    broad = sum(e >= BROAD_EVIDENCE for e in evidences)
    boost = 1 + f["breadth_bonus"] * max(broad - 1, 0)
    return 100 * (1 - exp(-sum(evidences) * boost / f["scale"]))
