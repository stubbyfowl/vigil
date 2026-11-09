"""Personal baselines from robust statistics."""

from dataclasses import dataclass
from statistics import median

from ..config import Config
from ..signals import Signal

MAD_TO_SD = 1.4826


@dataclass(frozen=True)
class Baseline:
    median: float
    sigma: float
    short_median: float
    n_obs: int
    learning: bool


def robust_stats(values: list[float]) -> tuple[float, float]:
    """Return the median and a MAD based estimate of the standard deviation."""
    mid = median(values)
    return mid, MAD_TO_SD * median(abs(v - mid) for v in values)


def window_sizes(sig: Signal, cfg: Config) -> tuple[int, int, int]:
    """Return short window, reference window and observations needed, all in readings."""
    b = cfg["baseline"]
    short = max(b["short_window_days"] // sig.cadence, b["min_observations"])
    reference = max(b["reference_window_days"] // sig.cadence, 2 * b["min_observations"])
    needed = max(b["learning_days"] // sig.cadence, b["min_observations"])
    return short, reference, needed


def compute_baseline(history: list[float], sig: Signal, cfg: Config) -> Baseline:
    """Build a baseline from past readings. Missing readings (NaN) are ignored."""
    clean = [v for v in history if v == v]
    short, reference, needed = window_sizes(sig, cfg)
    if not clean:
        return Baseline(float("nan"), float("nan"), float("nan"), 0, True)
    mid, sd = robust_stats(clean[-reference:])
    sigma = max(sd, cfg["baseline"]["sigma_floor"] * sig.noise)
    return Baseline(mid, sigma, median(clean[-short:]), len(clean), len(clean) < needed)
