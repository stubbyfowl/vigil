"""Measure Vigil against the planted events over 20 seeds. Results are computed, never typed in."""

import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config  # noqa: E402
from app.engine.pipeline import AstronautRun, run_mission  # noqa: E402
from app.signals import BY_ID, DRIFT_SIGNALS, Signal  # noqa: E402
from app.sim.generator import CREW, Mission, generate_mission  # noqa: E402

# Thresholds were tuned on seeds 1000 to 1019. These 20 were held out and used only for reporting.
SEEDS = list(range(2000, 2020))
# sensitive: mean plus 2 sd, many false alarms. quiet: mean plus 3 sd, a false alarm rate close to Vigil's.
FIXED_VARIANTS = {"sensitive": 2.0, "quiet": 3.0}
METHODS = ["z", "ewma", "cusum", "vote"]
HOURS = 24
FIXED_DOSE_RATE_LIMIT_FACTOR = 2.0  # population alarm at twice the normal dose rate
MERGE_GAP = 3  # alarm days this close together count as one alarm


def fixed_limit(sig: Signal, k: float) -> float:
    """A one-size-fits-all limit: population mean plus k sd in the bad direction."""
    spread = (sig.pop_sd**2 + sig.noise**2) ** 0.5
    return sig.pop_mean + k * spread if sig.bad == "up" else sig.pop_mean - k * spread


def fixed_alarm_days(mission: Mission, who: str, sig: Signal, k: float) -> list[int]:
    limit = fixed_limit(sig, k)
    values = mission.series[who][sig.id]
    return [i + 1 for i, v in enumerate(values) if v == v and (v >= limit if sig.bad == "up" else v <= limit)]


def event_window(ev: dict) -> tuple[int, int]:
    return ev["day"], int(ev["day"] + ev["duration_days"] + ev["ramp_days"])


def score_vigil(ev: dict, run: AstronautRun) -> dict:
    """Find the first day any planted signal of this event is flagged inside the event."""
    start, end = event_window(ev)
    names = [s["signal"] for s in ev["signals"]]
    first, triggers = None, set()
    for sid in names:
        for day, state in enumerate(run.signals[sid], start=1):
            if start <= day <= end and state.flagged:
                triggers.add(sid)
                first = day if first is None else min(first, day)
                break
    levels = [e.level for e in run.episodes if e.system == ev["system"] and e.open_day <= end and (e.close_day or 999) >= start]
    return {"first": first, "triggers": sorted(triggers), "level": max(levels, default=0)}


def score_fixed(ev: dict, mission: Mission, k: float) -> int | None:
    start, end = event_window(ev)
    days = [d for s in ev["signals"] for d in fixed_alarm_days(mission, ev["astronaut"], BY_ID[s["signal"]], k) if start <= d <= end]
    return min(days, default=None)


def storm_result(ev: dict, mission: Mission, runs: dict[str, AstronautRun]) -> dict:
    """Storm timing in hours. Vigil relays the simulated monitor's flag at the warning hour."""
    alerted = all(any(a["system"] == "radiation" for a in runs[w.id].alerts[ev["day"] - 1]) for w in CREW)
    limit = 76 * FIXED_DOSE_RATE_LIMIT_FACTOR
    crossings = [h for h in range(ev["warning_hour"], ev["end_hour"]) if mission.hourly_free["cmdr"][h] >= limit]
    return {
        "detected": alerted, "vigil_hours": ev["warning_hour"] - ev["onset_hour"],
        "fixed_hours": (crossings[0] - ev["onset_hour"]) if crossings else None, "level": 3 if alerted else 0,
    }


def excluded_days(who: str, truth: list[dict]) -> set[int]:
    """Days inside this person's planted events, plus a small tail while evidence fades."""
    days: set[int] = set()
    for ev in truth:
        if ev["astronaut"] == who:
            start, end = event_window(ev)
            days |= set(range(start, end + 8))
    return days


def merge_alarms(days: list[int]) -> list[int]:
    merged: list[int] = []
    for d in sorted(days):
        if not merged or d - last > MERGE_GAP:
            merged.append(d)
        last = d
    return merged


def false_alarms(mission: Mission, runs: dict[str, AstronautRun], who: str) -> dict:
    """Count alarms that started outside planted events, per person."""
    skip = excluded_days(who, mission.ground_truth)
    monitored = mission.days - len(skip & set(range(1, mission.days + 1)))
    episodes = [e for e in runs[who].episodes if e.open_day not in skip]
    fixed = {
        f"fixed_{name}": len(merge_alarms([d for s in DRIFT_SIGNALS for d in fixed_alarm_days(mission, who, s, k) if d not in skip]))
        for name, k in FIXED_VARIANTS.items()
    }
    return {
        "days": monitored, "l1": len(episodes), "l2": sum(e.level >= 2 for e in episodes),
        "l3": sum(e.level >= 3 for e in episodes), **fixed,
    }


def run_seed(seed: int, cfg: dict) -> dict:
    mission = generate_mission(seed, cfg["mission"]["length_days"])
    runs = run_mission(mission, cfg)
    events = {}
    for ev in mission.ground_truth:
        if ev["id"] == "solar_storm":
            events[ev["id"]] = storm_result(ev, mission, runs)
        else:
            events[ev["id"]] = {
                **score_vigil(ev, runs[ev["astronaut"]]),
                "fixed": {name: score_fixed(ev, mission, k) for name, k in FIXED_VARIANTS.items()},
            }
    return {"truth": mission.ground_truth, "events": events, "fa": {w.id: false_alarms(mission, runs, w.id) for w in CREW}}


def mean_sd(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "sd": None, "n": 0}
    return {"mean": round(st.mean(values), 2), "sd": round(st.stdev(values), 2) if len(values) > 1 else 0.0, "n": len(values)}


def per_100(results: list[dict], who: list[str], key: str) -> dict:
    rates = [100 * sum(r["fa"][w][key] for w in who) / sum(r["fa"][w]["days"] for w in who) for r in results]
    return mean_sd(rates)


def summarize_event(ev: dict, results: list[dict]) -> dict:
    n = len(results)
    rows = [r["events"][ev["id"]] for r in results]
    base = {k: ev[k] for k in ("id", "title", "day", "astronaut", "system")} | {"runs": n}
    if ev["id"] == "solar_storm":
        return base | {
            "unit": "hours", "detected": sum(r["detected"] for r in rows), "levels": dict(Counter(r["level"] for r in rows)),
            "vigil_vs_onset": mean_sd([r["vigil_hours"] for r in rows]),
            "fixed_alarm": mean_sd([r["fixed_hours"] for r in rows if r["fixed_hours"] is not None]),
            "triggers": {"dose_rate": n},
        }
    hit = [r for r in rows if r["first"] is not None]
    fixed = {}
    for name in FIXED_VARIANTS:
        both = [r for r in hit if r["fixed"][name] is not None]
        fixed[name] = {
            "detected": sum(r["fixed"][name] is not None for r in rows),
            "vs_onset": mean_sd([r["fixed"][name] - ev["day"] for r in rows if r["fixed"][name] is not None]),
            "lead_vigil_earlier": mean_sd([r["fixed"][name] - r["first"] for r in both]),
            "missed_by_fixed_found_by_vigil": sum(r["fixed"][name] is None for r in hit),
        }
    return base | {
        "unit": "days", "detected": len(hit), "levels": dict(Counter(r["level"] for r in rows)),
        "vigil_vs_onset": mean_sd([r["first"] - ev["day"] for r in hit]),
        "fixed": fixed,
        "triggers": dict(Counter(s for r in hit for s in r["triggers"])),
    }


def method_row(method: str, cfg: dict) -> dict:
    """Compare a single detector or the vote across the held-out seeds."""
    trial = {**cfg, "detector": {**cfg["detector"], "method": method}}
    results = [run_seed(s, trial) for s in SEEDS]
    truth = [e for e in results[0]["truth"] if e["id"] != "solar_storm"]
    delays = [r["events"][e["id"]]["first"] - e["day"] for e in truth for r in results if r["events"][e["id"]]["first"] is not None]
    found = sum(r["events"][e["id"]]["first"] is not None for e in truth for r in results)
    everyone = [w.id for w in CREW]
    return {
        "method": method, "detected": found, "total": len(truth) * len(results), "delay": mean_sd(delays),
        "false_alarms_per_100_days": per_100(results, everyone, "l1"),
    }


def _delay(row: dict, unit: str) -> str:
    return f"{row['mean']} {unit} (sd {row['sd']})" if row["n"] else "never"


def write_markdown(out: dict, path: Path) -> None:
    fa = out["false_alarms"]
    lines = [
        "# Detector results", "",
        "All data is synthetic. These numbers show the method works on simulated events we planted. They say nothing about real people.",
        "", f"Runs: {len(out['seeds'])} held-out seeds. Thresholds were tuned on different seeds. Numbers are mean and standard deviation across seeds.",
        "", "## Planted events", "",
        "Delay is days after event onset until the first flag on a planted signal. Events ramp up over several days, so some delay is expected.", "",
        "| Event | Who | Found | Delay after onset | Highest level reached (runs) | Signals that fired (runs) |", "|---|---|---|---|---|---|",
    ]
    for e in out["events"]:
        levels = ", ".join(f"L{k}: {n}" for k, n in sorted(e["levels"].items()))
        triggers = ", ".join(f"{k} {n}" for k, n in sorted(e["triggers"].items()))
        lines.append(f"| {e['title']} | {e['astronaut']} | {e['detected']}/{e['runs']} | {_delay(e['vigil_vs_onset'], e['unit'])} | {levels} | {triggers} |")
    storm = next(e for e in out["events"] if e["id"] == "solar_storm")
    lines += [
        "", f"The storm warning comes from the simulated solar monitor. Vigil relays it {abs(storm['vigil_vs_onset']['mean'])} hours before onset. Vigil does not predict storms. "
        f"A fixed dose rate alarm at twice normal fires {storm['fixed_alarm']['mean']} hours after onset.", "",
        "## Against fixed population limits", "",
        "A fixed limit is one number for everyone: population mean plus k standard deviations.",
        "**Sensitive** uses k = 2. **Quiet** uses k = 3, which has a false alarm rate closer to Vigil's. A positive lead means Vigil flagged first.", "",
        "| Event | Limit | Fixed found | Fixed delay | Vigil earlier by | Fixed missed, Vigil found |", "|---|---|---|---|---|---|",
    ]
    for e in out["events"]:
        for name, f in e.get("fixed", {}).items():
            lead = f["lead_vigil_earlier"]
            lead_text = f"{lead['mean']} days (sd {lead['sd']}, n={lead['n']})" if lead["n"] else "n/a"
            lines.append(f"| {e['title']} | {name} | {f['detected']}/{e['runs']} | {_delay(f['vs_onset'], 'days')} | {lead_text} | {f['missed_by_fixed_found_by_vigil']} |")
    lines += [
        "", "## False alarms per 100 monitored days, per person", "",
        "| Group | Vigil any alert | Vigil Level 2 or more | Vigil Level 3 | Fixed sensitive | Fixed quiet |", "|---|---|---|---|---|---|",
    ]
    for label, key in [("Quiet control", "quiet"), ("Non-event days, all crew", "non_event")]:
        row = fa[key]
        cells = [f"{row[k]['mean']} (sd {row[k]['sd']})" for k in ("l1", "l2", "l3", "fixed_sensitive", "fixed_quiet")]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += ["", "## Detector comparison", "", "| Method | Planted events found | Mean delay (days) | False alarms per 100 days |", "|---|---|---|---|"]
    for m in out["methods"]:
        lines.append(f"| {m['method']} | {m['detected']}/{m['total']} | {m['delay']['mean']} | {m['false_alarms_per_100_days']['mean']} |")
    lines += ["", "The solar storm is left out of this comparison because it does not use drift detectors.", ""]
    path.write_text("\n".join(lines))


def main() -> None:
    cfg = config.load_config()
    results = [run_seed(s, cfg) for s in SEEDS]
    everyone = [w.id for w in CREW]
    out = {
        "note": "Synthetic data. Thresholds are starting values, not clinical limits.",
        "seeds": SEEDS, "method": cfg["detector"]["method"],
        "events": [summarize_event(ev, results) for ev in results[0]["truth"]],
        "false_alarms": {
            name: {k: per_100(results, who, k) for k in ("l1", "l2", "l3", "fixed_sensitive", "fixed_quiet")}
            for name, who in {"quiet": ["ctl"], "non_event": everyone}.items()
        },
        "methods": [method_row(m, cfg) for m in METHODS],
    }
    config.SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    (config.SYNTHETIC_DIR / "results.json").write_text(json.dumps(out, indent=2))
    write_markdown(out, ROOT / "docs" / "results.md")
    print((ROOT / "docs" / "results.md").read_text())


if __name__ == "__main__":
    main()
