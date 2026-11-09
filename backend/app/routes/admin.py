"""Hidden admin screen: edit thresholds, delay, speed and which signals run."""

from typing import Any

from fastapi import APIRouter, HTTPException

from .. import config
from ..models import ThresholdsUpdate
from ..signals import DRIFT_SIGNALS
from .deps import live, now, store

router = APIRouter(prefix="/api/admin")


def _merge(base: dict[str, Any], new: dict[str, Any], path: str = "") -> None:
    """Copy new values into base. Unknown keys and wrong types are rejected."""
    for key, value in new.items():
        where = f"{path}{key}"
        if key not in base:
            raise HTTPException(422, f"Unknown setting: {where}")
        if isinstance(base[key], dict):
            if not isinstance(value, dict):
                raise HTTPException(422, f"{where} must be a group of settings.")
            _merge(base[key], value, f"{where}.")
        elif isinstance(base[key], bool) != isinstance(value, bool) or isinstance(base[key], list) != isinstance(value, list):
            raise HTTPException(422, f"{where} has the wrong type.")
        elif isinstance(base[key], int | float) and not isinstance(value, int | float):
            raise HTTPException(422, f"{where} must be a number.")
        elif isinstance(value, int | float) and not isinstance(value, bool) and value < 0:
            raise HTTPException(422, f"{where} cannot be negative.")
        else:
            base[key] = value


def _apply_runtime() -> None:
    sync = store.cfg["sync"]
    scale = sync["demo_time_scale"] if sync.get("scale_time", True) else 1
    live.queue.delay_s = sync["one_way_delay_minutes"] * 60 / scale
    live.queue.bandwidth = sync["bandwidth_kb_s"]
    live.days_per_second = float(store.cfg["mission"]["days_per_second"])
    live.set_day(live.day, now())


@router.get("/config")
def get_config() -> dict[str, Any]:
    return {"config": store.cfg, "signals": [{"id": s.id, "name": s.name} for s in DRIFT_SIGNALS]}


@router.put("/config")
def put_config(body: ThresholdsUpdate) -> dict[str, Any]:
    previous = config.load_config()
    updated = config.load_config()
    _merge(updated, body.values)
    known = {s.id for s in DRIFT_SIGNALS}
    if not set(updated["disabled_signals"]) <= known:
        raise HTTPException(422, "disabled_signals names an unknown signal.")
    config.save_config(updated)
    try:
        store.rebuild()
    except Exception as err:
        config.save_config(previous)
        store.rebuild()
        raise HTTPException(422, f"Those values do not work: {err}") from err
    _apply_runtime()
    return {"config": store.cfg}


@router.post("/reset")
def reset() -> dict[str, Any]:
    store.restore_defaults()
    _apply_runtime()
    return {"config": store.cfg}
