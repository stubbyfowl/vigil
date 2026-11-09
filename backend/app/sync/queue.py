"""Model of the Earth link: delay, priority, and lost link. Time is passed in, so tests are exact."""

from dataclasses import asdict, dataclass
from typing import Any

PRIORITY_LEVEL3 = 0
PRIORITY_NORMAL = 1


@dataclass
class Packet:
    id: int
    kind: str
    astronaut: str
    title: str
    priority: int
    size_kb: float
    mission_day: int
    payload: dict[str, Any]
    created_at: float
    sent_at: float | None = None
    tx_done_at: float | None = None
    arrives_at: float | None = None

    def state(self, now: float) -> str:
        """queued, sent (leaving the antenna), in_transit, or received."""
        if self.sent_at is None or self.tx_done_at is None or self.arrives_at is None:
            return "queued"
        if now < self.tx_done_at:
            return "sent"
        return "in_transit" if now < self.arrives_at else "received"


class SyncQueue:
    """One transmitter. Level 3 packets always leave first."""

    def __init__(self, delay_s: float, bandwidth_kb_s: float) -> None:
        self.delay_s, self.bandwidth = delay_s, bandwidth_kb_s
        self.packets: list[Packet] = []
        self.link_up = True
        self.busy_until = 0.0

    def enqueue(
        self, now: float, kind: str, astronaut: str, title: str, priority: int, size_kb: float, day: int, payload: dict
    ) -> Packet:
        packet = Packet(len(self.packets) + 1, kind, astronaut, title, priority, size_kb, day, payload, now)
        self.packets.append(packet)
        self.update(now)
        return packet

    def set_link(self, up: bool, now: float) -> None:
        self.link_up = up
        self.update(now)

    def update(self, now: float) -> None:
        """Start the next waiting packet whenever the link is up and the transmitter is free."""
        while self.link_up and now >= self.busy_until:
            waiting = [p for p in self.packets if p.sent_at is None]
            if not waiting:
                return
            packet = min(waiting, key=lambda p: (p.priority, p.id))
            packet.sent_at = now
            packet.tx_done_at = now + packet.size_kb / self.bandwidth
            packet.arrives_at = packet.tx_done_at + self.delay_s
            self.busy_until = packet.tx_done_at

    def view(self, now: float) -> list[dict[str, Any]]:
        """Packets for display, newest first, with seconds left in flight."""
        self.update(now)
        out = []
        for p in reversed(self.packets):
            row = asdict(p)
            row["state"] = p.state(now)
            row["seconds_left"] = max(0.0, round(p.arrives_at - now, 1)) if p.arrives_at else None
            row["flight_seconds"] = self.delay_s
            out.append(row)
        return out
