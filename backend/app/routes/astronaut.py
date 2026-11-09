"""Everything the astronaut's own tablet reads and writes."""

from typing import Any

from fastapi import APIRouter, HTTPException

from ..engine.alerts import PROTOCOLS
from ..models import AlertAction, CallEarth, CheckIn, ShareSet
from ..signals import DRIFT_SIGNALS, SIGNALS, SYSTEMS
from ..sim.generator import CREW
from ..store import series_payload
from ..sync.privacy import ground_card
from ..sync.queue import PRIORITY_LEVEL3, PRIORITY_NORMAL
from .deps import live, now, resolve_day, store

router = APIRouter(prefix="/api")
TREND_DAYS = 30
CHART_SIGNALS = 3
EARTH_DECISIONS = {
    0: ("none", "No need to call Earth.", "All systems are inside your normal. A routine summary goes out each week."),
    1: ("self", "Handle this on board.", "A small change. Follow the self-care step and recheck. Earth does not need to wait on this."),
    2: ("crew", "Tell the Medical Officer.", "The change is wider or longer. The crew can run a longer check before Earth could answer."),
    3: ("earth", "Send a priority packet now.", "A Level 3 condition is active. Act on the checklist while the packet travels."),
}


def _identity(who: Any) -> dict[str, Any]:
    return {"id": who.id, "name": who.name, "role": who.role, "tag": who.tag, "control": who.control}


@router.get("/crew")
def crew() -> dict[str, Any]:
    return {
        "crew": [_identity(w) for w in CREW],
        "systems": SYSTEMS,
        "signals": [{"id": s.id, "name": s.name, "unit": s.unit, "system": s.system} for s in SIGNALS],
    }


@router.get("/astronaut/{aid}")
def astronaut(aid: str, day: int | None = None) -> dict[str, Any]:
    who = store.who(aid)
    d = resolve_day(day)
    run = store.runs[aid]
    alerts = store.alerts(aid, d)
    alert_level = {a["system"]: a["level"] for a in alerts}
    systems = []
    for key, name in SYSTEMS.items():
        today = run.systems[key][d - 1]
        systems.append({
            "id": key, "name": name, **today, "level": alert_level.get(key, 0),
            "trend": [x["score"] for x in run.systems[key][max(0, d - TREND_DAYS): d]],
        })
    return {
        "astronaut": _identity(who), "day": d, "mission_days": store.mission.days, "systems": systems,
        "alerts": alerts, "all_clear": not alerts, "radiation": run.radiation[d - 1],
        "learning": all(s["learning"] for s in systems),
    }


@router.get("/astronaut/{aid}/system/{system}")
def system_detail(aid: str, system: str, day: int | None = None) -> dict[str, Any]:
    store.who(aid)
    if system not in SYSTEMS:
        raise HTTPException(404, f"No system named {system}.")
    d = resolve_day(day)
    run = store.runs[aid]
    wanted = [s.id for s in DRIFT_SIGNALS if s.system == system and s.id in run.signals]
    return {
        "system": system, "name": SYSTEMS[system], "day": d, **run.systems[system][d - 1],
        "signals": [series_payload(store, aid, sid, d) for sid in wanted],
    }


@router.get("/astronaut/{aid}/alert/{alert_id}")
def alert_detail(aid: str, alert_id: str, day: int | None = None) -> dict[str, Any]:
    store.who(aid)
    d = resolve_day(day)
    for past in range(d, 0, -1):
        match = next((a for a in store.alerts(aid, past, include_hidden=True) if a["id"] == alert_id), None)
        if match:
            ids = [s["signal"] for s in match["why"]["signals"][:CHART_SIGNALS] if s["signal"] in store.runs[aid].signals]
            protocol = PROTOCOLS.get(match["protocol"])
            return {
                "alert": match, "closed": past != d, "day": d,
                "charts": [series_payload(store, aid, sid, past, 60) for sid in ids],
                "protocol": protocol, "protocol_label": PROTOCOLS["_label"],
            }
    raise HTTPException(404, "This alert is not active on this mission day.")


@router.post("/astronaut/{aid}/alert/{alert_id}/action")
def alert_action(aid: str, alert_id: str, body: AlertAction) -> dict[str, Any]:
    d = resolve_day(None)
    current = alert_detail(aid, alert_id, d)["alert"]
    store.record_action(alert_id, body.action, d, current["level"])
    updated = next((a for a in store.alerts(aid, d, include_hidden=True) if a["id"] == alert_id), current)
    if body.action == "escalate":
        live.queue_level3(updated, d, now())
    return {"alert": updated, "action": body.action}


@router.post("/checkin")
def checkin(body: CheckIn) -> dict[str, Any]:
    d = resolve_day(None)
    return {"day": d, "journal_score": store.save_checkin(body, d), "text_kept": body.keep_text and bool(body.journal)}


@router.get("/astronaut/{aid}/radiation")
def radiation(aid: str, day: int | None = None) -> dict[str, Any]:
    store.who(aid)
    d = resolve_day(day)
    series = store.mission.series[aid]
    return {
        **store.runs[aid].radiation[d - 1], "day": d, "mission_days": store.mission.days,
        "daily_dose": [round(float(v), 2) for v in series["daily_dose"][max(0, d - TREND_DAYS): d]],
        "warning_usv_h": store.cfg["radiation"]["dose_rate_warn_usv_h"],
    }


@router.get("/astronaut/{aid}/share")
def get_share(aid: str) -> dict[str, bool]:
    store.who(aid)
    return store.share(aid)


@router.post("/astronaut/{aid}/share")
def set_share(aid: str, body: ShareSet) -> dict[str, bool]:
    store.who(aid)
    return store.set_share(aid, body.share_crew, body.share_ground)


@router.get("/astronaut/{aid}/earth")
def earth_decision(aid: str, day: int | None = None) -> dict[str, Any]:
    store.who(aid)
    d = resolve_day(day)
    alerts = store.alerts(aid, d, include_hidden=True)
    level = max((a["level"] for a in alerts), default=0)
    kind, title, detail = EARTH_DECISIONS[level]
    top = next((a for a in alerts if a["level"] == level), None)
    return {
        "level": level, "decision": kind, "title": title, "detail": detail, "reason": top["level_reason"] if top else None,
        "delay_minutes": store.cfg["sync"]["one_way_delay_minutes"], "share": store.share(aid),
        "preview": ground_card(store.runs[aid], d, alerts, store.share(aid)["share_ground"]),
    }


@router.post("/call-earth")
def call_earth(body: CallEarth) -> dict[str, Any]:
    who = store.who(body.astronaut)
    d = resolve_day(None)
    alerts = store.alerts(who.id, d, include_hidden=True)
    level = max((a["level"] for a in alerts), default=0)
    card = ground_card(store.runs[who.id], d, alerts, store.share(who.id)["share_ground"])
    priority = PRIORITY_LEVEL3 if level >= 3 else PRIORITY_NORMAL
    packet = live.queue.enqueue(now(), "call", who.id, f"{who.tag} call to Earth", priority, 32.0, d, card | {"note": body.note})
    return {"packet_id": packet.id, "state": packet.state(now()), "flight_seconds": live.queue.delay_s}


