"""Live missions write each packet for Earth as a file. The vehicle's comm system sends it and removes it.

Vigil never opens a network connection. The outbox folder is the whole contract:
one JSON file per packet, named so that sorting by name gives the send order.
"""

import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import db
from .queue import PRIORITY_LEVEL3


@dataclass(frozen=True)
class OutboxPacket:
    id: int
    file: str

    def state(self, now: float) -> str:
        return "in_outbox"


class Outbox:
    """Same calls as the simulated SyncQueue, so the screens need not care which mission is open."""

    def __init__(self, db_path: Path, folder: Path, delay_minutes: float, bandwidth_kb_s: float) -> None:
        self.db_path, self.folder = db_path, folder
        self.delay_s, self.bandwidth = delay_minutes * 60, bandwidth_kb_s
        self.link_up = True

    def enqueue(
        self, now: float, kind: str, astronaut: str, title: str, priority: int, size_kb: float, day: int,
        payload: dict[str, Any], ref: str | None = None,
    ) -> OutboxPacket:
        """Write one packet. A ref makes the call safe to repeat: the same ref is written once."""
        with db.connect(self.db_path) as con:
            if ref:
                old = con.execute("SELECT id, file FROM packets WHERE ref = ?", (ref,)).fetchone()
                if old:
                    return OutboxPacket(old["id"], old["file"])
            cursor = con.execute(
                "INSERT INTO packets (ref, kind, member, title, priority, size_kb, day, payload, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (ref, kind, astronaut, title, priority, size_kb, day, json.dumps(payload), time.time()),
            )
            packet_id = int(cursor.lastrowid or 0)
            # Level 3 sorts first, then oldest first.
            name = f"{'0' if priority == PRIORITY_LEVEL3 else '1'}-{packet_id:06d}-{kind}-{astronaut}.json"
            con.execute("UPDATE packets SET file = ? WHERE id = ?", (name, packet_id))
        body = {
            "vigil_packet": 1, "id": packet_id, "kind": kind, "member": astronaut, "title": title, "priority": priority,
            "mission_day": day, "created_at": datetime.now(UTC).isoformat(timespec="seconds"), "payload": payload,
        }
        self.folder.mkdir(parents=True, exist_ok=True)
        partial = self.folder / f".{name}.part"
        partial.write_text(json.dumps(body, indent=1))
        os.replace(partial, self.folder / name)  # the comm system never sees half a file
        return OutboxPacket(packet_id, name)

    def set_link(self, up: bool, now: float) -> None:
        raise ValueError("A live mission has no simulated link. The vehicle's comm system sends the outbox.")

    def update(self, now: float) -> None:
        return None

    def rows(self, limit: int = 50) -> list[dict[str, Any]]:
        with db.connect(self.db_path) as con:
            found = con.execute("SELECT * FROM packets ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) | {"payload": json.loads(r["payload"])} for r in found]

    def view(self, now: float) -> list[dict[str, Any]]:
        """Newest first. A file still in the folder has not been picked up yet."""
        return [
            {
                "id": r["id"], "kind": r["kind"], "astronaut": r["member"], "title": r["title"], "priority": r["priority"],
                "size_kb": r["size_kb"], "mission_day": r["day"], "file": r["file"],
                "state": "in_outbox" if (self.folder / r["file"]).exists() else "picked_up",
                "seconds_left": None, "flight_seconds": self.delay_s,
            }
            for r in self.rows()
        ]
