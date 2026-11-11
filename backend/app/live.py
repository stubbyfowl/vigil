"""The shared mission clock, packets it produces, and the Demo Director."""

from dataclasses import asdict, dataclass
from typing import Any

from .store import Store
from .sync.privacy import ground_card
from .sync.queue import PRIORITY_LEVEL3, PRIORITY_NORMAL, SyncQueue

DIRECTOR_DAYS_PER_SECOND = 6.0
SUMMARY_EVERY_DAYS = 7
LEVEL3_PACKET_KB = 48.0
SUMMARY_PACKET_KB = 16.0


@dataclass(frozen=True)
class Beat:
    day: int
    astronaut: str
    route: str
    caption: str
    hold: float


def _first_alert(store: Store, event_id: str) -> dict[str, Any] | None:
    """Find the planted event's first alert in the real engine output. Prefer Level 2 or more."""
    ev = next((e for e in store.mission.ground_truth if e["id"] == event_id), None)
    if not ev:
        return None
    window = store.runs[ev["astronaut"]].alerts[ev["day"] - 1: ev["day"] + ev["duration_days"]]
    found = [a for day in window for a in day if a["system"] == ev["system"]]
    return next((a for a in found if a["level"] >= 2), found[0] if found else None)


def build_beats(store: Store) -> list[Beat]:
    """The story, with every day taken from what the engine actually flagged."""
    beats = [
        Beat(1, "eng", "/", "Day 1. Vigil has no baseline for anyone yet.", 7),
        Beat(11, "eng", "/", "Day 11. Each person now has a baseline from 10 days of readings.", 5),
    ]
    immune = _first_alert(store, "immune_stress")
    if immune:
        beats += [
            Beat(immune["day"], "eng", "/", f"Day {immune['day']}. Lena says she feels fine. Several of her immune readings have moved at once.", 6),
            Beat(immune["day"], "eng", f"/alert/{immune['id']}", "The alert is written for Lena, with the numbers behind it one tap away.", 9),
        ]
    slide = _first_alert(store, "behavior_slide")
    if slide:
        beats.append(Beat(slide["day"], "plt", f"/alert/{slide['id']}", "Tomas has slept less and rated his mood lower for two weeks. The Medical Officer is told.", 9))
    if store.mission.storm:
        beats += [
            Beat(120, "eng", "/radiation", "Day 120. The solar monitor warns of a storm 2 hours ahead, and the shelter checklist opens.", 9),
            Beat(120, "eng", "/ground", "A Level 3 packet goes to the front of the queue. Earth reads it 20 minutes later.", 8),
        ]
    heart = _first_alert(store, "heart_drift")
    if heart:
        beats += [
            Beat(heart["day"], "cmdr", f"/alert/{heart['id']}", "Ana's resting heart rate is under every population limit and well above her own baseline.", 8),
            Beat(heart["day"], "cmdr", "/explainer", "Two crew members with the same heart rate. For one of them it is normal. For the other it is high.", 12),
        ]
    beats.append(Beat(store.mission.days, "eng", "/results", "Tested on 20 simulated missions kept out of tuning, with every false alarm counted.", 10))
    return beats


class Live:
    def __init__(self, store: Store, now: float) -> None:
        self.store = store
        self.day_float = float(store.cfg["mission"]["start_day"])
        self.running = False
        self.days_per_second = float(store.cfg["mission"]["days_per_second"])
        self.last_time = now
        self.packeted: set[tuple[str, int]] = set()
        self.beats: list[Beat] = []
        self.beat_index = -1
        self.holding = False
        self.hold_until = 0.0
        self.finished = False
        self.queue = self._new_queue()

    def _new_queue(self) -> SyncQueue:
        s = self.store.cfg["sync"]
        scale = s["demo_time_scale"] if s.get("scale_time", True) else 1
        return SyncQueue(s["one_way_delay_minutes"] * 60 / scale, s["bandwidth_kb_s"])

    @property
    def day(self) -> int:
        return self.store.clamp_day(int(self.day_float))

    # Clock

    def set_day(self, day: int, now: float) -> None:
        """Jump without creating packets. Used by the scrubber."""
        self.tick(now)
        self.day_float = float(self.store.clamp_day(day))

    def tick(self, now: float) -> None:
        """Move time forward to now. Nothing runs in the background."""
        elapsed = now - self.last_time
        self.last_time = now
        if self.beat_index >= 0:
            self._tick_director(elapsed, now)
        elif self.running:
            self._advance(elapsed * self.days_per_second, now)
            if self.day_float >= self.store.mission.days:
                self.running = False
        self.queue.update(now)

    def _advance(self, days: float, now: float, limit: float | None = None) -> None:
        before = self.day
        cap = float(self.store.mission.days if limit is None else limit)
        self.day_float = min(self.day_float + days, cap)
        for day in range(before + 1, self.day + 1):
            self._emit_packets(day, now)

    def _emit_packets(self, day: int, now: float) -> None:
        """Level 3 alerts go straight to the queue. Each person sends a weekly summary."""
        store = self.store
        for who in store.crew:
            alerts = store.alerts(who.id, day, include_hidden=True)
            for alert in alerts:
                self.queue_level3(alert, day, now)
            if day % SUMMARY_EVERY_DAYS == 0 and not who.control:
                card = ground_card(store.runs[who.id], day, alerts, store.share(who.id)["share_ground"])
                self.queue.enqueue(now, "summary", who.id, f"{who.tag} weekly summary", PRIORITY_NORMAL, SUMMARY_PACKET_KB, day, card)

    def queue_level3(self, alert: dict[str, Any], day: int, now: float) -> None:
        key = (alert["id"], 3)
        if alert["level"] >= 3 and key not in self.packeted:
            self.packeted.add(key)
            payload = {"system": alert["system_name"], "level": 3, "reason": alert["level_reason"]}
            tag = self.store.who(alert["astronaut"]).tag
            self.queue.enqueue(now, "level3", alert["astronaut"], f"{tag} {alert['system_name']} Level 3", PRIORITY_LEVEL3, LEVEL3_PACKET_KB, day, payload)

    # Demo Director

    def start_demo(self, now: float) -> None:
        self.store.reset_interactive()
        self.queue = self._new_queue()
        self.packeted = set()
        self.beats = build_beats(self.store)
        self.beat_index, self.holding, self.finished, self.running = 0, False, False, False
        self.day_float = 1.0
        self.last_time = now

    def stop_demo(self) -> None:
        self.beat_index, self.holding = -1, False

    def next_beat(self, now: float) -> None:
        """Skip ahead: finish the move, or end the current hold."""
        if self.beat_index < 0:
            return
        if self.holding:
            self._leave_beat()
        else:
            self._advance(max(self.beats[self.beat_index].day - self.day_float, 0), now, self.beats[self.beat_index].day)
            self._arrive(now)

    def _leave_beat(self) -> None:
        self.holding = False
        self.beat_index += 1
        if self.beat_index >= len(self.beats):
            self.beat_index, self.finished = -1, True

    def _arrive(self, now: float) -> None:
        self.holding = True
        self.hold_until = now + self.beats[self.beat_index].hold

    def _tick_director(self, elapsed: float, now: float) -> None:
        if self.holding:
            if now >= self.hold_until:
                self._leave_beat()
            return
        beat = self.beats[self.beat_index]
        self._advance(elapsed * DIRECTOR_DAYS_PER_SECOND, now, beat.day)
        if self.day_float >= beat.day:
            self._arrive(now)

    def demo_view(self) -> dict[str, Any]:
        active = self.beat_index >= 0
        view: dict[str, Any] = {"active": active, "finished": self.finished, "total": len(self.beats)}
        if active:
            beat = self.beats[self.beat_index]
            view |= asdict(beat) | {"index": self.beat_index, "holding": self.holding}
            if not self.holding:
                view["route"] = "/"  # the home screen plays while time moves
                view["caption"] = f"Mission day {self.day}"
        return view

    def snapshot(self, now: float) -> dict[str, Any]:
        self.tick(now)
        return {
            "day": self.day, "mission_days": self.store.mission.days, "running": self.running,
            "days_per_second": self.days_per_second, "version": self.store.version,
            "link_up": self.queue.link_up, "demo": self.demo_view(),
            "delay_minutes": self.store.cfg["sync"]["one_way_delay_minutes"],
            "flight_seconds": self.queue.delay_s,
        }




class MissionClock:
    """A live mission follows the calendar. Level 3 alerts and weekly summaries go to the outbox by themselves."""

    def __init__(self, store: Store, now: float, outbox: Any) -> None:
        self.store = store
        self.queue = outbox
        self.running = False
        self.days_per_second = 0.0
        self._seen = (-1, -1)
        self.tick(now)

    @property
    def day(self) -> int:
        return self.store.mission.days

    def tick(self, now: float) -> None:
        """Rebuild when the date changes. Send what today requires, once."""
        if self.store.current_day() != self.store.mission.days:
            self.store.rebuild()
        seen = (self.store.mission.days, self.store.version)
        if seen != self._seen:
            self._seen = seen
            self._emit_packets(self.day, now)

    def _emit_packets(self, day: int, now: float) -> None:
        store = self.store
        for who in store.crew:
            alerts = store.alerts(who.id, day, include_hidden=True)
            for alert in alerts:
                self.queue_level3(alert, day, now)
            if day % SUMMARY_EVERY_DAYS == 0:
                card = ground_card(store.runs[who.id], day, alerts, store.share(who.id)["share_ground"])
                self.queue.enqueue(now, "summary", who.id, f"{who.tag} weekly summary", PRIORITY_NORMAL, SUMMARY_PACKET_KB, day, card,
                                   ref=f"summary:{who.id}:{day}")

    def queue_level3(self, alert: dict[str, Any], day: int, now: float) -> None:
        if alert["level"] >= 3:
            tag = self.store.who(alert["astronaut"]).tag
            payload = {"system": alert["system_name"], "level": 3, "reason": alert["level_reason"]}
            self.queue.enqueue(now, "level3", alert["astronaut"], f"{tag} {alert['system_name']} Level 3", PRIORITY_LEVEL3, LEVEL3_PACKET_KB,
                               day, payload, ref=f"level3:{alert['id']}")

    def set_day(self, day: int, now: float) -> None:
        raise ValueError("A live mission follows the calendar. Only the demo mission can jump in time.")

    def start_demo(self, now: float) -> None:
        raise ValueError("The Demo Director runs only in the demo mission.")

    def next_beat(self, now: float) -> None:
        return None

    def stop_demo(self) -> None:
        return None

    def snapshot(self, now: float) -> dict[str, Any]:
        self.tick(now)
        return {
            "day": self.day, "mission_days": self.store.info["length_days"], "running": False, "days_per_second": 0.0,
            "version": self.store.version, "link_up": True, "demo": {"active": False, "finished": False, "total": 0},
            "delay_minutes": self.store.cfg["sync"]["one_way_delay_minutes"], "flight_seconds": self.queue.delay_s,
        }
