"""Shared app state. One mission and one clock per server."""

import time

from ..live import Live
from ..store import Store

store = Store()
live = Live(store, time.monotonic())


def now() -> float:
    return time.monotonic()


def resolve_day(day: int | None) -> int:
    """Use the requested day, or the mission clock if none was given."""
    return store.clamp_day(day) if day is not None else live.snapshot(now())["day"]
