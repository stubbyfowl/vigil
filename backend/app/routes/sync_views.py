"""Crew and Ground screens, and the Earth link."""

from typing import Any

from fastapi import APIRouter

from ..models import LinkSet
from ..sim.generator import CREW
from ..sync.privacy import crew_card, ground_card
from .deps import live, now, resolve_day, store

router = APIRouter(prefix="/api")


@router.get("/crew-view")
def crew_view(day: int | None = None) -> dict[str, Any]:
    d = resolve_day(day)
    cards = [crew_card(store.runs[w.id], d, store.alerts(w.id, d), store.share(w.id)["share_crew"]) for w in CREW if not w.control]
    watching = sum(c["max_level"] > 0 or any(s["status"] != "green" for s in c["systems"]) for c in cards)
    summary = "All crew inside their normal." if not watching else f"{watching} of {len(cards)} crew need attention."
    return {"day": d, "crew": cards, "summary": summary}


@router.get("/ground")
def ground(day: int | None = None) -> dict[str, Any]:
    d = resolve_day(day)
    cards = [ground_card(store.runs[w.id], d, store.alerts(w.id, d, include_hidden=True), store.share(w.id)["share_ground"]) for w in CREW]
    t = now()
    return {
        "day": d, "crew": cards, "level3": [a | {"astronaut": c["tag"]} for c in cards for a in c["level3"]],
        "packets": live.queue.view(t), "link_up": live.queue.link_up,
        "delay_minutes": store.cfg["sync"]["one_way_delay_minutes"], "flight_seconds": live.queue.delay_s,
    }


@router.post("/link")
def set_link(body: LinkSet) -> dict[str, bool]:
    live.queue.set_link(body.up, now())
    return {"link_up": live.queue.link_up}
