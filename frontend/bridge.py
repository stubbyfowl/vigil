"""Connects the QML screens to the engine, in the same process. Holds who is signed in at this station."""

import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from app import config
from app.auth import CREW_ROLES, AuthError
from app.views import PUBLIC, Vigil
from PySide6.QtCore import Property, QEvent, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QPageSize, QPdfWriter, QTextDocument
from voice import VoiceInput, is_available

CLOCK_MS = 50
UNDO_SECONDS_MS = 8000
IDLE_CHECK_MS = 1000
INPUT_EVENTS = {QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress, QEvent.Type.TouchBegin, QEvent.Type.Wheel}
CHANGES_STATE = {
    "set_share", "call_earth", "set_link", "set_clock", "demo_start", "demo_next", "demo_stop", "checkin", "put_config", "reset_config",
    "log_readings", "delete_entry", "import_file", "add_member", "update_member", "set_auto_lock", "archive_mission",
}
DESIGN_VERSION = 2  # the aurora redesign; older saved themes reset once to the new default
DEFAULT_PREFS: dict[str, Any] = {"astronaut": "eng", "theme": "dark", "welcomed": False, "reduce_motion": False, "chose_demo": False, "design": DESIGN_VERSION, "narrator": False, "zoom": 1.0}
PROBLEMS = (LookupError, ValueError, TypeError, PermissionError, AuthError)
ZOOM_STEPS = (1.0, 1.15, 1.3)
# Sound goes through the computer's own offline tools. None of them use the network.
PLAYERS = (("afplay",), ("paplay",), ("pw-play",), ("aplay", "-q"), ("ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"))
SPEAKERS = (("say", "-v", "Daniel", "-r", "165"), ("espeak-ng", "-s", "140"), ("espeak", "-s", "140"), ("spd-say", "-w"))


def find_tool(options: tuple[tuple[str, ...], ...]) -> tuple[str, ...] | None:
    return next((cmd for cmd in options if shutil.which(cmd[0])), None)


def plain(value: Any) -> Any:
    """JSON the screens can parse: no NaN, no numpy types."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [plain(v) for v in value]
    if isinstance(value, np.generic):
        return plain(value.item())
    return value


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
    voiceChanged = Signal()
    voiceFinal = Signal(str, arguments=["text"])
    sessionChanged = Signal()
    stageChanged = Signal()
    lockedChanged = Signal()
    missionChanged = Signal()
    playingChanged = Signal()

    def __init__(self, vigil: Vigil, parent: QObject | None = None, station: str = "vehicle") -> None:
        super().__init__(parent)
        self.vigil = vigil
        self.station = station
        self.open_ground_window = lambda: None  # set by main.py
        self._voice = VoiceInput(self)
        self._voice_available = is_available()
        self._voice_on = False
        self._voice_heard = ""
        self._voice.partial.connect(self._on_voice_partial)
        self._voice.finished.connect(self._on_voice_finished)
        self._voice.failed.connect(self._on_voice_failed)
        self._palettes = json.loads((config.FRONTEND_DIR / "palette.json").read_text())
        self._prefs = dict(DEFAULT_PREFS)
        if config.PREFS_PATH.exists():
            saved = json.loads(config.PREFS_PATH.read_text())
            if saved.get("design") != DESIGN_VERSION:
                saved |= {"theme": "dark", "design": DESIGN_VERSION}
            self._prefs |= saved
        self._snap = vigil.live_state()
        self._route = "/"
        self._history: list[str] = []
        self._undo: dict[str, str] | None = None
        self._session: dict[str, Any] | None = None
        self._locked = False
        self._stage = self._resting_stage()
        self._store_seen = vigil.store
        self._last_input = time.monotonic()
        self._auto_lock_s = 0.0
        self._undo_timer = QTimer(self, singleShot=True, interval=UNDO_SECONDS_MS, timeout=self._clear_undo)
        self._timer = QTimer(self, interval=CLOCK_MS, timeout=self.tick)
        self._timer.start()
        self._idle_timer = QTimer(self, interval=IDLE_CHECK_MS, timeout=self._check_idle)
        self._idle_timer.start()
        if parent is not None:
            parent.installEventFilter(self)

    def _resting_stage(self) -> str:
        """Where this station starts when nobody is signed in."""
        if self.station == "vehicle" and self.vigil.mode == "demo" and not self.vigil.mission_exists() and not self._prefs["chose_demo"]:
            return "welcome"
        return "signin"

    @Slot()
    def tick(self) -> None:
        """Advance the mission clock and tell the screens what changed."""
        if self.vigil.store is not self._store_seen:  # the other window opened a different mission
            self._mission_opened()
            self._end_session()
            return
        old, self._snap = self._snap, self.vigil.live_state()
        new = self._snap
        for key, signal in (("day", self.dayChanged), ("version", self.versionChanged), ("running", self.runningChanged), ("link_up", self.linkChanged)):
            if old[key] != new[key]:
                signal.emit()
        if old["mission_days"] != new["mission_days"]:
            self.missionChanged.emit()
        if old["demo"] != new["demo"]:
            self.demoChanged.emit()
            demo = new["demo"]
            if demo["active"]:
                self._set_astronaut_pref(demo["astronaut"])
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

    @Property(int, notify=missionChanged)
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

    @Property(str, notify=missionChanged)
    def mode(self) -> str:
        return self.vigil.mode

    @Property(bool, notify=missionChanged)
    def isDemo(self) -> bool:
        return self.vigil.mode == "demo"

    @Property(str, constant=True)
    def stationName(self) -> str:
        return self.station

    # Who is signed in

    @Property("QVariant", notify=sessionChanged)
    def session(self) -> dict:
        return self._session or {}

    @Property(bool, notify=sessionChanged)
    def signedIn(self) -> bool:
        return self._session is not None

    @Property(str, notify=sessionChanged)
    def role(self) -> str:
        return self._session["role"] if self._session else ""

    @Property(str, notify=stageChanged)
    def stage(self) -> str:
        return self._stage

    @Property(bool, notify=lockedChanged)
    def locked(self) -> bool:
        return self._locked

    def _set_stage(self, stage: str) -> None:
        if stage != self._stage:
            self._stage = stage
            self.stageChanged.emit()

    def _start_session(self, user: dict[str, Any]) -> None:
        self._session = {k: user[k] for k in ("id", "name", "role", "role_name", "tag", "must_change")}
        self._session["previous_sign_in"] = user.get("previous_sign_in")
        self._locked = False
        self._last_input = time.monotonic()
        self._auto_lock_s = self.vigil.mission_info()["auto_lock_minutes"] * 60
        self._history = []
        self._route = "/"
        self.sessionChanged.emit()
        self.lockedChanged.emit()
        self.astronautChanged.emit()
        self.routeChanged.emit()
        self._set_stage("app")

    @Slot(str, str, result=str)
    def signIn(self, member: str, pin: str) -> str:
        """Returns an empty string on success, or the reason it failed."""
        try:
            self._start_session(self.vigil.sign_in(member, pin, self.station))
        except PROBLEMS as err:
            return str(err)
        return ""

    @Slot()
    def signOut(self) -> None:
        if self._session:
            self.vigil.note_session(self._session["id"], "signed_out")
            if self.vigil.mode == "demo":
                self.vigil.live.stop_demo()
        self._end_session()

    def _end_session(self) -> None:
        self._set_stage(self._resting_stage())  # unload the screens first, so none asks for data with nobody signed in
        self.stop_sound()  # the next person should not hear someone else's album
        self._session = None
        self._locked = False
        self._clear_undo()
        self._history = []
        self._route = "/"
        self.sessionChanged.emit()
        self.lockedChanged.emit()
        self.astronautChanged.emit()
        self.routeChanged.emit()
        self._set_stage(self._resting_stage())

    @Slot()
    def lock(self) -> None:
        self._lock("locked")

    def _lock(self, why: str) -> None:
        if self._session and not self._locked:
            self.vigil.note_session(self._session["id"], why)
            self._locked = True
            self.lockedChanged.emit()

    @Slot(str, result=str)
    def unlock(self, pin: str) -> str:
        if not self._session:
            return "Nobody is signed in."
        try:
            self.vigil.unlock(self._session["id"], pin)
        except PROBLEMS as err:
            return str(err)
        self._locked = False
        self._last_input = time.monotonic()
        self.lockedChanged.emit()
        return ""

    @Slot(str, str, result=str)
    def changePin(self, old: str, new: str) -> str:
        if not self._session:
            return "Nobody is signed in."
        try:
            self.vigil.change_pin(self._session["id"], old, new)
        except PROBLEMS as err:
            return str(err)
        self._session["must_change"] = False
        self.sessionChanged.emit()
        return ""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 (Qt name)
        if event.type() in INPUT_EVENTS:
            self._last_input = time.monotonic()
        return False

    @Slot()
    def _check_idle(self) -> None:
        """Lock the screen after the Commander's chosen idle time. Never during the Demo Director."""
        idle = time.monotonic() - self._last_input
        if self._session and not self._locked and self._auto_lock_s and not self._snap["demo"]["active"] and idle >= self._auto_lock_s:
            self._lock("auto_locked")

    # Choosing and creating a mission

    @Slot()
    def startSetup(self) -> None:
        self._set_stage("setup")

    @Slot()
    def leaveSetup(self) -> None:
        self._set_stage(self._resting_stage())

    @Slot()
    def chooseDemo(self) -> None:
        self._prefs["chose_demo"] = True
        self._save_prefs()
        self.openMission("demo")

    @Slot(str, result=str)
    def setupMission(self, args_json: str) -> str:
        try:
            result = self.vigil.setup_mission(**json.loads(args_json))
        except PROBLEMS as err:
            return str(err)
        self._mission_opened()
        self._start_session(result["member"])
        self._go("/accounts", remember=False)
        return ""

    @Slot(str, result=str)
    def openMission(self, mode: str) -> str:
        """Returns an empty string on success, or why the mission could not open."""
        try:
            self.vigil.open(mode)
        except PROBLEMS as err:
            return str(err)
        if self._session:
            self.vigil.note_session(self._session["id"], "signed_out")
        self._end_session()  # unload the screens before the new mission's data arrives
        self._mission_opened()
        return ""

    def _mission_opened(self) -> None:
        self._store_seen = self.vigil.store
        self._snap = self.vigil.live_state()
        self.missionChanged.emit()
        self.versionChanged.emit()
        self.dayChanged.emit()
        self.demoChanged.emit()

    # Choices the person makes

    def _get_astronaut(self) -> str:
        """Whose data the screens show. A crew member always sees their own. The Presenter can switch."""
        if self._session and self._session["role"] in CREW_ROLES:
            return self._session["id"]
        return self._prefs["astronaut"]

    def _set_astronaut_pref(self, value: str) -> None:
        if value != self._prefs["astronaut"]:
            self._prefs["astronaut"] = value
            self._save_prefs()
            self.astronautChanged.emit()

    def _set_astronaut(self, value: str) -> None:
        if not self._session or self._session["role"] == "presenter":
            self._set_astronaut_pref(value)

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

    def _get_narrator(self) -> bool:
        return self._prefs.get("narrator", False)

    def _set_narrator(self, value: bool) -> None:
        self._prefs["narrator"] = value
        self._save_prefs()

    narrator = Property(bool, _get_narrator, _set_narrator, notify=prefsChanged)

    def _get_zoom(self) -> float:
        return float(self._prefs.get("zoom", 1.0))

    def _set_zoom(self, value: float) -> None:
        self._prefs["zoom"] = min(ZOOM_STEPS[-1], max(ZOOM_STEPS[0], round(float(value), 2)))
        self._save_prefs()

    # Text and controls size for every page: Standard, Large or Largest.
    zoom = Property(float, _get_zoom, _set_zoom, notify=prefsChanged)

    # Heart rate album playback and the narrator's voice

    _player: subprocess.Popen | None = None
    _speaker: subprocess.Popen | None = None
    _playing = ""

    @Property(bool, constant=True)
    def canPlay(self) -> bool:  # noqa: N802 (Qt name)
        return find_tool(PLAYERS) is not None

    @Property(bool, constant=True)
    def canSpeak(self) -> bool:  # noqa: N802 (Qt name)
        return find_tool(SPEAKERS) is not None

    @Property(str, notify=playingChanged)
    def playing(self) -> str:
        if self._player is not None and self._player.poll() is not None:
            self._player, self._playing = None, ""
        return self._playing

    @Slot(str, result=str)
    def playTrack(self, path: str) -> str:  # noqa: N802 (Qt name)
        """Play one album track. Only files Vigil made in its album folder."""
        file = Path(path).resolve()
        if file.parent != (config.EXPORT_DIR / "album").resolve() or file.suffix != ".wav" or not file.is_file():
            return "That file is not one of Vigil's album tracks."
        command = find_tool(PLAYERS)
        if command is None:
            return f"No audio player was found on this computer. The track is saved at {file}."
        self.stopTrack()
        self._player = subprocess.Popen([*command, str(file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._playing = str(file)
        self.playingChanged.emit()
        QTimer.singleShot(500, self._watch_player)
        return ""

    def _watch_player(self) -> None:
        if self._player is None:
            return
        if self._player.poll() is None:
            QTimer.singleShot(500, self._watch_player)
        else:
            self._player, self._playing = None, ""
            self.playingChanged.emit()

    @Slot()
    def stopTrack(self) -> None:  # noqa: N802 (Qt name)
        if self._player is not None:
            self._player.terminate()
        self._player, self._playing = None, ""
        self.playingChanged.emit()

    @Slot(str, result=str)
    def speak(self, text: str) -> str:
        """Read a line aloud with the computer's offline voice."""
        command = find_tool(SPEAKERS)
        if command is None:
            return "No offline voice was found on this computer."
        if command[0] == "say" and sys.platform == "darwin" and "Daniel" not in subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout:
            command = ("say",)
        if self._speaker is not None:
            self._speaker.terminate()
        self._speaker = subprocess.Popen([*command, text[:500]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ""

    def stop_sound(self) -> None:
        """Called when the app quits, so nothing keeps playing after the window closes."""
        self.stopTrack()
        if self._speaker is not None:
            self._speaker.terminate()

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

    @Slot()
    def openGround(self) -> None:
        self.open_ground_window()

    # Everything else goes through one door, which checks who is asking

    def _request(self, name: str, args: dict[str, Any]) -> Any:
        # The mission name and the list of names stay readable while locked, so the sign-in screen always works.
        if self._locked and name not in PUBLIC:
            raise PermissionError("The screen is locked.")
        return self.vigil.request(self._session, name, args)

    @Slot(str, str, result=str)
    def ask(self, name: str, args_json: str) -> str:
        """Run one named engine call and return JSON. Errors come back as {"error": text}."""
        args = json.loads(args_json)
        args.pop("v", None)  # only there so QML re-reads when the data version changes
        try:
            result = self._request(name, args)
        except PROBLEMS as err:
            result = {"error": str(err)}
        if name == "set_auto_lock" and "error" not in result:
            self._auto_lock_s = result["auto_lock_minutes"] * 60
        if name == "archive_mission" and "error" not in result:
            self._end_session()  # unload the screens before they look for the archived crew
            self._mission_opened()
        elif name in CHANGES_STATE:
            self.tick()
        return json.dumps(plain(result))

    @Slot(result=str)
    def exportReport(self) -> str:
        """Write a one-page PDF health summary for the person on screen."""
        try:
            report = self._request("report", {"id": self.astronaut})
        except PROBLEMS as err:
            return json.dumps({"error": str(err)})
        path = Path(report["file"])
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = QPdfWriter(str(path))
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setTitle("Vigil health summary")
        doc = QTextDocument()
        doc.setDefaultFont(QFont("Public Sans", 10))
        doc.setHtml(report["html"])
        doc.print_(writer)
        return json.dumps({"path": str(path)})

    # Voice check-in

    @Property(bool, constant=True)
    def voiceAvailable(self) -> bool:
        return self._voice_available

    @Property(bool, notify=voiceChanged)
    def voiceListening(self) -> bool:
        return self._voice_on

    @Property(str, notify=voiceChanged)
    def voiceHeard(self) -> str:
        return self._voice_heard

    def _set_voice(self, on: bool, heard: str) -> None:
        self._voice_on, self._voice_heard = on, heard
        self.voiceChanged.emit()

    @Slot()
    def voiceToggle(self) -> None:
        if self._voice_on:
            self._voice.stop()
        else:
            self._set_voice(True, "")
            self._voice.start()

    @Slot(str)
    def _on_voice_partial(self, text: str) -> None:
        self._set_voice(True, text)

    @Slot(str)
    def _on_voice_finished(self, text: str) -> None:
        self._set_voice(False, "")
        if text:
            self.voiceFinal.emit(text)

    @Slot(str)
    def _on_voice_failed(self, message: str) -> None:
        self._set_voice(False, message)

    # Undo: people can take back what they just did

    @Slot(str, str, str, result=str)
    def alertAction(self, owner: str, alert_id: str, action: str) -> str:
        try:
            self._request("alert_action", {"id": owner, "alert_id": alert_id, "action": action})
        except PROBLEMS as err:
            return str(err)
        words = {"done": "Marked done.", "snooze": "Snoozed for 2 hours.", "escalate": "Escalated."}
        self._undo = {"alert": alert_id, "owner": owner, "text": words[action]}
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
            try:
                self._request("undo_alert_action", {"alert_id": self._undo["alert"], "id": self._undo["owner"]})
            except PROBLEMS:
                return
            self._clear_undo()
            self.versionTouched()

    @Slot()
    def _clear_undo(self) -> None:
        self._undo = None
        self._undo_timer.stop()
        self.undoChanged.emit()
