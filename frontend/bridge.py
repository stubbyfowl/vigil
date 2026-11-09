"""Connects the QML screens to the engine, in the same process."""

import json
from typing import Any

from app import config
from app.views import Vigil
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

CLOCK_MS = 50
UNDO_SECONDS_MS = 8000
QUERIES = {
    "crew", "astronaut", "system_detail", "alert_detail", "radiation", "sensors", "get_share", "set_share", "earth_decision", "call_earth",
    "crew_view", "ground", "set_link", "set_clock", "demo_start", "demo_next", "demo_stop", "timeline", "explainer", "results", "about",
    "checkin", "get_config", "put_config", "reset_config",
}
CHANGES_STATE = {"set_share", "call_earth", "set_link", "set_clock", "demo_start", "demo_next", "demo_stop", "checkin", "put_config", "reset_config"}
DEFAULT_PREFS: dict[str, Any] = {"astronaut": "eng", "theme": "dark", "welcomed": False, "reduce_motion": False}


class Bridge(QObject):
    dayChanged = Signal()
    versionChanged = Signal()
    runningChanged = Signal()
    linkChanged = Signal()
    demoChanged = Signal()
    routeChanged = Signal()
    astronautChanged = Signal()
    prefsChanged = Signal()
    undoChanged = Signal()

    def __init__(self, vigil: Vigil, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.vigil = vigil
        self._palettes = json.loads((config.FRONTEND_DIR / "palette.json").read_text())
        self._prefs = dict(DEFAULT_PREFS)
        if config.PREFS_PATH.exists():
            self._prefs |= json.loads(config.PREFS_PATH.read_text())
        self._snap = vigil.live_state()
        self._route = "/"
        self._history: list[str] = []
        self._undo: dict[str, str] | None = None
        self._undo_timer = QTimer(self, singleShot=True, interval=UNDO_SECONDS_MS, timeout=self._clear_undo)
        self._timer = QTimer(self, interval=CLOCK_MS, timeout=self.tick)
        self._timer.start()

    @Slot()
    def tick(self) -> None:
        """Advance the mission clock and tell the screens what changed."""
        old, self._snap = self._snap, self.vigil.live_state()
        new = self._snap
        for key, signal in (("day", self.dayChanged), ("version", self.versionChanged), ("running", self.runningChanged), ("link_up", self.linkChanged)):
            if old[key] != new[key]:
                signal.emit()
        if old["demo"] != new["demo"]:
            self.demoChanged.emit()
            demo = new["demo"]
            if demo["active"]:
                self.astronaut = demo["astronaut"]
                self._go(demo["route"], remember=False)

    def _go(self, route: str, remember: bool = True) -> None:
        if route != self._route:
            if remember:
                self._history.append(self._route)
            self._route = route
            self.routeChanged.emit()

    def _save_prefs(self) -> None:
        config.PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.PREFS_PATH.write_text(json.dumps(self._prefs))
        self.prefsChanged.emit()

    # Read-only state for bindings

    @Property(int, notify=dayChanged)
    def day(self) -> int:
        return self._snap["day"]

    @Property(int, constant=True)
    def missionDays(self) -> int:
        return self._snap["mission_days"]

    @Property(int, notify=versionChanged)
    def version(self) -> int:
        return self._snap["version"]

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._snap["running"]

    @Property(bool, notify=linkChanged)
    def linkUp(self) -> bool:
        return self._snap["link_up"]

    @Property(int, notify=versionChanged)
    def delayMinutes(self) -> int:
        return int(self._snap["delay_minutes"])

    @Property(float, notify=versionChanged)
    def flightSeconds(self) -> float:
        return self._snap["flight_seconds"]

    @Property("QVariant", notify=demoChanged)
    def demo(self) -> dict:
        return self._snap["demo"]

    @Property("QVariant", constant=True)
    def palettes(self) -> dict:
        return self._palettes

    @Property(str, notify=routeChanged)
    def route(self) -> str:
        return self._route

    # Choices the person makes

    def _get_astronaut(self) -> str:
        return self._prefs["astronaut"]

    def _set_astronaut(self, value: str) -> None:
        if value != self._prefs["astronaut"]:
            self._prefs["astronaut"] = value
            self._save_prefs()
            self.astronautChanged.emit()

    astronaut = Property(str, _get_astronaut, _set_astronaut, notify=astronautChanged)

    def _get_theme(self) -> str:
        return self._prefs["theme"]

    def _set_theme(self, value: str) -> None:
        self._prefs["theme"] = value
        self._save_prefs()

    theme = Property(str, _get_theme, _set_theme, notify=prefsChanged)

    def _get_reduce(self) -> bool:
        return self._prefs["reduce_motion"]

    def _set_reduce(self, value: bool) -> None:
        self._prefs["reduce_motion"] = value
        self._save_prefs()

    reduceMotion = Property(bool, _get_reduce, _set_reduce, notify=prefsChanged)

    @Property(bool, notify=prefsChanged)
    def welcomed(self) -> bool:
        return self._prefs["welcomed"]

    @Slot()
    def acknowledgeWelcome(self) -> None:
        self._prefs["welcomed"] = True
        self._save_prefs()

    # Navigation

    @Slot(str)
    def navigate(self, route: str) -> None:
        self._go(route)

    @Slot()
    def back(self) -> None:
        self._go(self._history.pop() if self._history else "/", remember=False)

    # Everything else goes through one door

    @Slot(str, str, result=str)
    def ask(self, name: str, args_json: str) -> str:
        """Run one named engine call and return JSON. Errors come back as {"error": text}."""
        if name not in QUERIES:
            return json.dumps({"error": f"Unknown request: {name}"})
        args = json.loads(args_json)
        args.pop("v", None)  # only there so QML re-reads when the data version changes
        try:
            result = getattr(self.vigil, name)(**args)
        except (LookupError, ValueError, TypeError) as err:
            result = {"error": str(err)}
        if name in CHANGES_STATE:
            self.tick()
        return json.dumps(result)

    # Undo: people can take back what they just did

    @Slot(str, str, str, result=str)
    def alertAction(self, owner: str, alert_id: str, action: str) -> str:
        try:
            self.vigil.alert_action(owner, alert_id, action)
        except (LookupError, ValueError) as err:
            return str(err)
        words = {"done": "Marked done.", "snooze": "Snoozed for 2 hours.", "escalate": "Escalated."}
        self._undo = {"alert": alert_id, "text": words[action]}
        self._undo_timer.start()
        self.undoChanged.emit()
        self.tick()
        self.versionTouched()
        return ""

    def versionTouched(self) -> None:
        self.vigil.store.version += 1
        self.tick()

    @Property(str, notify=undoChanged)
    def undoText(self) -> str:
        return self._undo["text"] if self._undo else ""

    @Slot()
    def undo(self) -> None:
        if self._undo:
            self.vigil.undo_alert_action(self._undo["alert"])
            self._clear_undo()
            self.versionTouched()

    @Slot()
    def _clear_undo(self) -> None:
        self._undo = None
        self._undo_timer.stop()
        self.undoChanged.emit()
