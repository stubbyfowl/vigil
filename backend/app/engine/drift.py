"""Per-signal drift detection: robust z-score, EWMA chart, CUSUM, and a vote."""

from dataclasses import dataclass
from math import isnan, sqrt

import numpy as np

from ..config import Config
from ..signals import Signal
from . import fast
from .baseline import compute_baseline
from .fusion import evidence

METHODS = ("z", "ewma", "cusum")
PLAIN_NAMES = {"z": "one-day jump test", "ewma": "EWMA trend test", "cusum": "CUSUM change test"}


def ewma_step(previous: float, r: float, lam: float) -> float:
    """Advance an exponentially weighted average by one reading."""
    return lam * r + (1 - lam) * previous


def ewma_limit(lam: float, width: float) -> float:
    """Long-run control limit for the EWMA of unit variance readings."""
    return width * sqrt(lam / (2 - lam))


def cusum_step(previous: float, r: float, k: float) -> float:
    """Advance a one-sided CUSUM by one reading. k is the allowance."""
    return max(0.0, previous + r - k)


def combine(fired: dict[str, bool], method: str, votes_needed: int) -> bool:
    """Apply the configured method: one detector, or a vote of all three."""
    return sum(fired.values()) >= votes_needed if method == "vote" else fired[method]


@dataclass(frozen=True)
class SignalDay:
    """Everything known about one signal on one day."""

    value: float  # NaN when there was no reading today
    last_value: float  # most recent reading, today or earlier
    median: float
    sigma: float
    short_median: float
    learning: bool
    ewma: float
    fired: tuple[str, ...]
    flagged: bool
    drift_days: int
    evidence: float


class SignalTracker:
    """Walks one signal through a mission, one day at a time."""

    def __init__(self, sig: Signal, cfg: Config, method: str | None = None) -> None:
        self.sig, self.cfg = sig, cfg
        d = cfg["detector"]
        self.method = method or d["method"]
        self.limit = ewma_limit(d["ewma_lambda"], d["ewma_l"])
        self.sign = 1 if sig.bad == "up" else -1
        self.history: list[float] = []
        self.day = 0
        self.ewma = self.cusum = 0.0
        self.flag_start: int | None = None
        self.true_run = self.false_run = 0
        self.last_value = float("nan")
        self.fired: tuple[str, ...] = ()

    def _detect(self, value: float, median: float, sigma: float) -> None:
        d = self.cfg["detector"]
        r = self.sign * (value - median) / sigma
        self.ewma = ewma_step(self.ewma, r, d["ewma_lambda"])
        self.cusum = cusum_step(self.cusum, r, d["cusum_k"])
        fired = {"z": r >= d["z_limit"], "ewma": self.ewma >= self.limit, "cusum": self.cusum >= d["cusum_h"]}
        self.fired = tuple(m for m in METHODS if fired[m])
        self._debounce(combine(fired, self.method, d["votes_needed"]))

    def _debounce(self, active: bool) -> None:
        """Daily signals must agree on several readings in a row to turn a flag on or off."""
        d = self.cfg["detector"]
        persist, release = (d["persist_readings"], d["release_readings"]) if self.sig.cadence == 1 else (1, 1)
        self.true_run = self.true_run + 1 if active else 0
        self.false_run = 0 if active else self.false_run + 1
        if self.flag_start is None and self.true_run >= persist:
            self.flag_start = self.day - self.true_run + 1
        elif self.flag_start is not None and self.false_run >= release:
            self.flag_start = None

    def update(self, value: float) -> SignalDay:
        """Take today's reading, or NaN if missing, and return today's state."""
        self.day += 1
        base = compute_baseline(self.history, self.sig, self.cfg)
        if not isnan(value):
            self.last_value = value
            if not base.learning:
                self._detect(value, base.median, base.sigma)
            # A flagged reading stays out of the baseline, so illness cannot become the new normal.
            # After max_freeze_days the change is accepted as the new normal.
            if self.flag_start is None or self.day - self.flag_start > self.cfg["baseline"]["max_freeze_days"]:
                self.history.append(value)
        flagged = self.flag_start is not None
        return SignalDay(
            value=value, last_value=self.last_value, median=base.median, sigma=base.sigma,
            short_median=base.short_median, learning=base.learning, ewma=self.ewma, fired=self.fired,
            flagged=flagged, drift_days=self.day - self.flag_start + 1 if self.flag_start else 0,
            evidence=evidence(self.ewma, self.limit, flagged, self.cfg),
        )


def track_signal(sig: Signal, values: np.ndarray, cfg: Config, method: str | None = None) -> list[SignalDay]:
    """Run one signal over a whole mission, in C++ if it is built and in Python if not."""
    chosen = method or cfg["detector"]["method"]
    if not fast.available():
        tracker = SignalTracker(sig, cfg, chosen)
        return [tracker.update(float(v)) for v in values]
    d = cfg["detector"]
    out = fast.track(sig, values, cfg, chosen, ewma_limit(d["ewma_lambda"], d["ewma_l"]))
    return [
        SignalDay(value=v, last_value=lv, median=m, sigma=sg, short_median=sm, learning=le, ewma=ew, fired=fi, flagged=fl, drift_days=dd, evidence=ev)
        for v, lv, m, sg, sm, le, ew, fi, fl, dd, ev in zip(
            out["value"], out["last_value"], out["median"], out["sigma"], out["short_median"], out["learning"],
            out["ewma"], out["fired"], out["flagged"], out["drift_days"], out["evidence"], strict=True,
        )
    ]
