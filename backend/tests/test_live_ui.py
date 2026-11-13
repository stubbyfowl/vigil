"""The interface on a real mission, signed in as each role. No QML errors, no small targets, no simulated badge."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "frontend"))

from app import config  # noqa: E402
from app.views import Vigil  # noqa: E402
from main import create_engine, quick_window  # noqa: E402

TARGETS = ("QQuickAbstractButton", "QQuickTextField", "QQuickSlider", "QQuickTextArea")
CREW_ROUTES = ["/", "/log", "/checkin", "/sensors", "/radiation", "/crew", "/earth", "/profile", "/system/heart", "/about",
               "/chat", "/replay", "/album", "/gut"]
PEOPLE = {"ana": "4826", "priya": "7391", "lena": "5170"}


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    home = tmp_path_factory.mktemp("liveui")
    with pytest.MonkeyPatch.context() as mp:
        for name, sub in (("MISSION_DB_PATH", "mission.db"), ("OUTBOX_DIR", "outbox"), ("IMPORT_DIR", "import"),
                          ("EXPORT_DIR", "exports"), ("BACKUP_DIR", "backups")):
            mp.setattr(config, name, home / sub)
        start = date.today() - timedelta(days=11)
        today = [start]
        vigil = Vigil(today=lambda: today[0])
        vigil.setup_mission("Analog 1", start.isoformat(), 90, "Ana Reyes", "4826")
        for name, role, pin in (("Priya Nair", "medical", "7391"), ("Lena Novak", "crew", "5170"), ("Kai Sato", "ground", "8402")):
            vigil.request({"id": "ana", "role": "commander"}, "add_member", {"name": name, "role": role, "pin": pin})
            vigil.accounts.set_pin(name.split()[0].lower(), pin, must_change=False)
        for i in range(12):
            today[0] = start + timedelta(days=i)
            vigil.live.tick(0)
            vigil.request({"id": "lena", "role": "crew"}, "log_readings", {"values": {"resting_hr": 60 + (8 if i > 8 else 0), "temp": 36.6}})
        app = QGuiApplication.instance() or QGuiApplication([])
        warnings: list[str] = []
        engine, bridge = create_engine(app, vigil, lambda w: warnings.extend(x.toString() for x in w))
        bridge.acknowledgeWelcome()
        yield {"vigil": vigil, "bridge": bridge, "window": quick_window(engine.rootObjects()[0]), "warnings": warnings, "app": app}


def items(item):
    for child in item.childItems():
        if child.isVisible():
            yield child
            yield from items(child)


def check_screen(live, route):
    live["warnings"].clear()
    live["bridge"].navigate(route)
    QTest.qWait(150)
    root = live["window"].contentItem()
    page = live["window"].findChild(QObject, "page")
    assert page.property("progress") == 1.0 and page.property("item") is not None
    small = [(i.metaObject().className(), round(i.width()), round(i.height())) for i in items(root)
             if isinstance(i, QQuickItem) and any(i.inherits(t) for t in TARGETS) and (i.width() < 55.5 or i.height() < 55.5)]
    assert small == []
    assert not any(i.property("text") == "Simulated data" for i in items(root))
    assert live["warnings"] == []


@pytest.mark.parametrize("member", sorted(PEOPLE))
@pytest.mark.parametrize("route", CREW_ROUTES)
def test_every_crew_screen_for_every_role(live, member, route):
    bridge = live["bridge"]
    if bridge.session.get("id") != member:
        bridge.signOut()
        assert bridge.signIn(member, PEOPLE[member]) == ""
    check_screen(live, route)


@pytest.mark.parametrize("route", ["/accounts", "/audit", "/admin"])
def test_commander_screens(live, route):
    bridge = live["bridge"]
    if bridge.session.get("id") != "ana":
        bridge.signOut()
        assert bridge.signIn("ana", PEOPLE["ana"]) == ""
    check_screen(live, route)


def test_log_screen_saves_and_flags_a_bad_value(live):
    bridge = live["bridge"]
    bridge.signOut()
    bridge.signIn("lena", PEOPLE["lena"])
    bridge.navigate("/log")
    QTest.qWait(150)
    screen = live["window"].findChild(QObject, "page").property("item")
    screen.setProperty("values", {"spo2": "120"})
    screen.metaObject().invokeMethod(screen, "save")
    QTest.qWait(50)
    errors = screen.property("errors")
    assert "spo2" in (errors.toVariant() if hasattr(errors, "toVariant") else errors)
    screen.setProperty("values", {"spo2": "97"})
    screen.metaObject().invokeMethod(screen, "save")
    QTest.qWait(50)
    assert "saved" in screen.property("saved")


def test_mission_control_window_needs_its_own_sign_in(live):
    bridge = live["bridge"]
    live["warnings"].clear()
    bridge.openGround()
    QTest.qWait(200)
    station = bridge.ground_bridge
    assert station.stage == "signin"
    assert "on the vehicle" in station.signIn("lena", PEOPLE["lena"])  # crew cannot sign in at the ground station
    assert station.signIn("kai", "8402") == ""
    QTest.qWait(200)
    assert live["warnings"] == []
    assert "error" in station.ask("astronaut", '{"id": "lena"}')
    station.signOut()


def test_lena_cannot_sign_in_as_mission_control_on_the_vehicle(live):
    assert "Mission Control" in live["bridge"].signIn("kai", "8402")
