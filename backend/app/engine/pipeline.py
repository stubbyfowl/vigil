"""Run the whole engine over a mission, day by day."""

from dataclasses import dataclass, field
from math import isnan
from typing import Any

import numpy as np

from ..config import Config
from ..signals import DRIFT_SIGNALS, SYSTEMS, Signal
from ..sim.generator import CREW, Astronaut, Mission
from .alerts import write_alert
from .baseline import window_sizes
from .drift import SignalDay, track_signal
from .escalation import Facts, decide
from .fusion import drift_score
from .radiation import radiation_alert, radiation_day
from .risk import signal_confidence, status_for

RECENT_DAYS = 14


@dataclass
class Episode:
    """One continuous stretch of drift in one system."""

    system: str
    open_day: int
    level: int = 0
    close_day: int | None = None
    reason: str = ""
    level2_day: int | None = None
    level2_score: float = 0.0
    first_day_at: dict[int, int] = field(default_factory=dict)
    signals: set[str] = field(default_factory=set)
    quiet_days: int = 0
    alert: dict[str, Any] | None = None


@dataclass
class AstronautRun:
    who: Astronaut
    signals: dict[str, list[SignalDay]]
    systems: dict[str, list[dict[str, Any]]]
    alerts: list[list[dict[str, Any]]]
    episodes: list[Episode]
    radiation: list[dict[str, Any]]


def _hard_limit_hit(flagged: list[tuple[Signal, SignalDay]], cfg: Config) -> str | None:
    """Return a plain description of the first hard limit crossed today."""
    for sig, day in flagged:
        limits = cfg["hard_limits"].get(sig.id, {})
        if isnan(day.value):
            continue
        if ("high" in limits and day.value >= limits["high"]) or ("low" in limits and day.value <= limits["low"]):
            return sig.name.lower()
    return None


def _members(system: str, active: list[Signal]) -> tuple[list[Signal], list[Signal]]:
    primary = [s for s in active if s.system == system]
    return primary, [s for s in active if system in s.also]


def _flagged_today(
    system: str, today: dict[str, SignalDay], active: list[Signal]
) -> list[tuple[Signal, SignalDay]]:
    """Flagged signals, strongest first. Linked signals count only with a primary one."""
    primary, linked = _members(system, active)
    flagged = [(s, today[s.id]) for s in primary if today[s.id].flagged]
    if flagged:
        flagged += [(s, today[s.id]) for s in linked if today[s.id].flagged]
    return sorted(flagged, key=lambda p: (-p[1].evidence, -p[1].drift_days, p[0].id))


def _step_episode(ep: Episode, day: int, flagged: list[tuple[Signal, SignalDay]], score: float, who: str, cfg: Config) -> None:
    """Update one open episode with today's flags."""
    ep.signals |= {s.id for s, _ in flagged}
    facts = Facts(
        system=SYSTEMS[ep.system].lower(), flagged=len(flagged),
        longest_drift_days=max(d.drift_days for _, d in flagged),
        hard_limit=_hard_limit_hit(flagged, cfg),
        days_since_level2=None if ep.level2_day is None else day - ep.level2_day,
        score_rise_since_level2=score - ep.level2_score,
    )
    level, reason = decide(facts, cfg)
    if level > ep.level:
        ep.level, ep.reason = level, reason
        ep.first_day_at[level] = day
    if ep.level >= 2 and ep.level2_day is None:
        ep.level2_day, ep.level2_score = day, score
    ep.alert = write_alert(who, ep.system, ep.open_day, day, ep.level, ep.reason, flagged, score)


def _confidence(system: str, active: list[Signal], series: dict[str, np.ndarray], today: dict[str, SignalDay], d: int, cfg: Config) -> float:
    values = []
    for sig in _members(system, active)[0]:
        window = series[sig.id][max(0, d - RECENT_DAYS + 1): d + 1]
        expected = max(int(np.ceil(len(window) / sig.cadence)), 1)
        history = series[sig.id][: d + 1]
        n_obs = int(np.sum(~np.isnan(history)))
        needed = window_sizes(sig, cfg)[2]
        values.append(signal_confidence(int(np.sum(~np.isnan(window))), expected, n_obs, needed))
    return round(float(np.mean(values)), 2) if values else 0.0


def run_astronaut(who: Astronaut, mission: Mission, cfg: Config, method: str | None = None) -> AstronautRun:
    """Walk one person through the mission."""
    active = [s for s in DRIFT_SIGNALS if s.id not in cfg.get("disabled_signals", [])]
    series = mission.series[who.id]
    signal_days: dict[str, list[SignalDay]] = {s.id: track_signal(s, series[s.id], cfg, method) for s in active}
    system_days: dict[str, list[dict[str, Any]]] = {k: [] for k in SYSTEMS}
    open_eps: dict[str, Episode] = {}
    episodes: list[Episode] = []
    alerts_by_day: list[list[dict[str, Any]]] = []
    rad_days: list[dict[str, Any]] = []

    for d in range(mission.days):
        day = d + 1
        today = {sid: states[d] for sid, states in signal_days.items()}
        alerts: list[dict[str, Any]] = []
        for system in SYSTEMS:
            primary, _ = _members(system, active)
            flagged = _flagged_today(system, today, active)
            score = drift_score([today[s.id].evidence for s in primary], cfg)
            ep = open_eps.get(system)
            if flagged and ep is None:
                ep = open_eps[system] = Episode(system, day)
                episodes.append(ep)
            if ep is not None:
                if flagged:
                    ep.quiet_days = 0
                    _step_episode(ep, day, flagged, score, who.id, cfg)
                else:
                    ep.quiet_days += 1
                    if ep.quiet_days >= cfg["escalation"]["close_after_quiet_days"]:
                        ep.close_day = day
                        del open_eps[system]
                        ep = None
            if ep is not None and ep.alert:
                alerts.append({**ep.alert, "day": day, "recovering": ep.quiet_days > 0})
            level = ep.level if ep is not None else 0
            daily = [today[s.id] for s in primary if s.cadence == 1]
            system_days[system].append({
                "score": round(score), "status": status_for(score, level, cfg), "level": level,
                "confidence": _confidence(system, active, series, today, d, cfg),
                "learning": sum(x.learning for x in daily) > len(daily) / 2,
                "flagged": [s.id for s, _ in flagged],
            })
        rad = radiation_day(mission, who, day, cfg)
        rad_days.append(rad)
        storm_alert = radiation_alert(mission, who, day, rad, cfg)
        if storm_alert:
            alerts.append(storm_alert)
        alerts_by_day.append(sorted(alerts, key=lambda a: -a["level"]))
    return AstronautRun(who, signal_days, system_days, alerts_by_day, episodes, rad_days)


def run_mission(mission: Mission, cfg: Config, method: str | None = None, crew: tuple[Astronaut, ...] = CREW) -> dict[str, AstronautRun]:
    """Run every crew member."""
    return {who.id: run_astronaut(who, mission, cfg, method) for who in crew}
