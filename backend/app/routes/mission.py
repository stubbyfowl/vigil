"""Mission clock, demo control, replay, and evaluation results."""

import asyncio
import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .. import config
from ..models import ClockSet
from ..signals import SYSTEMS
from ..sim.generator import CREW
from ..store import series_payload
from .deps import live, now, store

router = APIRouter(prefix="/api")
STATUS_CODE = {"green": "g", "yellow": "y", "red": "r"}
EXPLAINER_WINDOW = 50


@router.get("/live")
def live_state() -> dict[str, Any]:
    return live.snapshot(now())


@router.post("/clock")
def set_clock(body: ClockSet) -> dict[str, Any]:
    if body.days_per_second is not None:
        live.days_per_second = body.days_per_second
    if body.day is not None:
        live.set_day(body.day, now())
    if body.running is not None:
        live.tick(now())
        live.running = body.running
    return live.snapshot(now())


@router.post("/demo/start")
def demo_start() -> dict[str, Any]:
    live.start_demo(now())
    return live.snapshot(now())


@router.post("/demo/next")
def demo_next() -> dict[str, Any]:
    live.next_beat(now())
    return live.snapshot(now())


@router.post("/demo/stop")
def demo_stop() -> dict[str, Any]:
    live.stop_demo()
    return live.snapshot(now())


@router.get("/timeline")
def timeline() -> dict[str, Any]:
    """Compact health state for every person and day, so scrubbing needs no server calls."""
    crew = []
    for who in CREW:
        run = store.runs[who.id]
        crew.append({
            "id": who.id, "tag": who.tag, "name": who.name, "control": who.control,
            "status": {k: "".join(STATUS_CODE[d["status"]] for d in run.systems[k]) for k in SYSTEMS},
            "level": [max((a["level"] for a in day), default=0) for day in run.alerts],
        })
    events = [{k: e[k] for k in ("id", "title", "day", "astronaut", "system")} for e in store.mission.ground_truth]
    return {"mission_days": store.mission.days, "systems": SYSTEMS, "crew": crew, "events": events}


def _explainer_day() -> tuple[int, str, str, float] | None:
    """Find a real day when a flagged person and an unflagged person read the same heart rate."""
    series = store.mission.series
    best = None
    for flagged_who in CREW:
        states = store.runs[flagged_who.id].signals["resting_hr"]
        for i, state in enumerate(states):
            if not state.flagged or state.value != state.value:
                continue
            for other in CREW:
                peer = store.runs[other.id].signals["resting_hr"][i]
                if other.id == flagged_who.id or peer.flagged or peer.learning or other.control:
                    continue
                gap = abs(float(series[other.id]["resting_hr"][i]) - state.value)
                # Prefer an exact match, then the widest gap between the two personal baselines.
                rank = (gap, -abs(peer.median - state.median))
                if gap == gap and (best is None or rank < best[0]):
                    best = (rank, i + 1, flagged_who.id, other.id, state.value)
    return best[1:] if best else None


@router.get("/explainer")
def explainer() -> dict[str, Any]:
    found = _explainer_day()
    if not found:
        return {"available": False}
    day, flagged, normal, value = found
    people = []
    for who, verdict in ((flagged, "alert"), (normal, "normal")):
        member = store.who(who)
        states = store.runs[who].signals["resting_hr"][day - 1]
        people.append({
            "id": who, "name": member.name, "role": member.role, "verdict": verdict,
            "value": float(store.mission.series[who]["resting_hr"][day - 1]),
            "median": round(states.median, 1), "low": round(states.median - 2 * states.sigma, 1),
            "high": round(states.median + 2 * states.sigma, 1), "drift_days": states.drift_days,
            "chart": series_payload(store, who, "resting_hr", day, EXPLAINER_WINDOW),
        })
    return {"available": True, "day": day, "value": value, "people": people}


@router.get("/results")
def results() -> dict[str, Any]:
    path: Path = config.SYNTHETIC_DIR / "results.json"
    if not path.exists():
        return {"available": False}
    return {"available": True, **json.loads(path.read_text())}


@router.get("/about")
def about() -> dict[str, Any]:
    ranges = json.loads((config.DATA_DIR / "real_ranges.json").read_text())
    table = (config.ROOT / "SOURCES.md").read_text().split("## Numbers")[0]
    rows = re.findall(r"^\| (?!Source|---)(.+?) \| (.+?) \| (.+?) \|$", table, flags=re.M)
    must_verify = sum(v["status"] == "must_verify" for group in ("signals", "radiation", "communication") for v in ranges[group].values())
    return {
        "sources": [{"name": n, "use": u, "status": s} for n, u, s in rows],
        "must_verify_count": must_verify,
        "radiation": ranges["radiation"],
        "statement": "All crew data in Vigil is synthetic. Thresholds are starting values, not clinical limits. "
                     "Vigil gives decision support, not a diagnosis.",
    }


async def _day_stream(start: int, end: int, speed: float) -> AsyncIterator[str]:
    for day in range(start, end + 1):
        readings = {
            who.id: {s: (None if v[day - 1] != v[day - 1] else float(v[day - 1])) for s, v in store.mission.series[who.id].items()}
            for who in CREW
        }
        yield f"data: {json.dumps({'day': day, 'readings': readings})}\n\n"
        await asyncio.sleep(1 / speed)


@router.get("/sim/stream")
def sim_stream(start: int = 1, end: int | None = None, speed: float = 10.0) -> StreamingResponse:
    """Stream mission days as server-sent events at the chosen days per second."""
    last = store.clamp_day(end if end is not None else store.mission.days)
    return StreamingResponse(_day_stream(store.clamp_day(start), last, max(speed, 0.1)), media_type="text/event-stream")
