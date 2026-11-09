"""Load the real interface offscreen. Every screen must render with no QML errors."""

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "frontend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.views import Vigil  # noqa: E402
from main import create_engine, quick_window  # noqa: E402

TARGETS = ("QQuickAbstractButton", "QQuickTextField", "QQuickSlider", "QQuickTextArea")
ROUTES = [
    "/", "/alert/eng-immune-46", "/system/immune", "/checkin", "/radiation", "/crew", "/ground", "/earth", "/sensors",
    "/timeline", "/explainer", "/delay", "/results", "/about", "/admin",
]


class Ui:
    def __init__(self):
        self.app = QGuiApplication.instance() or QGuiApplication([])
        self.warnings = []
        self.vigil = Vigil()
        self.engine, self.bridge = create_engine(self.app, self.vigil, lambda w: self.warnings.extend(x.toString() for x in w))
        self.window = quick_window(self.engine.rootObjects()[0])

    def show(self, route, day=49):
        self.vigil.set_clock(day=day, running=False)
        self.bridge.tick()
        self.bridge.navigate(route)
        QTest.qWait(150)

    def items(self, item=None):
        item = item or self.window.contentItem()
        for child in item.childItems():
            if child.isVisible():
                yield child
                yield from self.items(child)


@pytest.fixture(scope="module")
def ui():
    built = Ui()
    assert built.engine.rootObjects(), built.warnings
    built.bridge.acknowledgeWelcome()
    return built


@pytest.mark.parametrize("route", ROUTES)
def test_screen_renders_without_qml_errors(ui, route):
    ui.warnings.clear()
    ui.show(route)
    page = ui.window.findChild(QObject, "page")
    assert page.property("progress") == 1.0 and page.property("item") is not None
    assert ui.warnings == []


@pytest.mark.parametrize("route", ROUTES)
def test_touch_targets_are_at_least_56(ui, route):
    ui.show(route)
    small = [
        (type(i).__name__, i.metaObject().className(), round(i.width()), round(i.height()))
        for i in ui.items() if isinstance(i, QQuickItem) and any(i.inherits(t) for t in TARGETS) and (i.width() < 55.5 or i.height() < 55.5)
    ]
    assert small == []


@pytest.mark.parametrize("route", ROUTES)
def test_simulated_badge_is_on_every_screen(ui, route):
    ui.show(route)
    assert any(i.property("text") == "Simulated data" for i in ui.items())


@pytest.mark.parametrize("theme", ["dark", "light", "night"])
def test_themes_load(ui, theme):
    ui.warnings.clear()
    ui.bridge.theme = theme
    ui.show("/")
    ui.bridge.theme = "dark"
    assert ui.warnings == []


def test_unknown_screen_has_a_way_back(ui):
    ui.show("/nowhere")
    assert any(i.property("text") == "That screen does not exist." for i in ui.items())


def test_unknown_alert_explains_itself(ui):
    ui.warnings.clear()
    ui.show("/alert/eng-heart-999")
    assert any("not active" in str(i.property("text")) for i in ui.items())
    assert ui.warnings == []


def test_second_window_opens(ui):
    ui.warnings.clear()
    ui.window.setProperty("groundOpen", True)
    QTest.qWait(200)
    assert ui.window.findChild(QObject, "groundWindow").property("visible")
    ui.window.setProperty("groundOpen", False)
    assert ui.warnings == []


def test_demo_drives_the_screens(ui):
    ui.warnings.clear()
    ui.vigil.demo_start()
    ui.bridge.tick()
    assert ui.bridge.demo["active"]
    for _ in range(12):
        if not ui.vigil.live.demo_view()["active"]:
            break
        ui.vigil.demo_next()
        ui.bridge.tick()
        QTest.qWait(80)
    ui.vigil.demo_stop()
    ui.bridge.tick()
    assert ui.warnings == []


def test_undo_restores_a_dismissed_alert(ui):
    ui.vigil.store.reset_interactive()
    ui.show("/")
    alert = ui.vigil.astronaut("eng", day=49)["alerts"][0]
    assert ui.bridge.alertAction("eng", alert["id"], "done") == ""
    assert alert["id"] not in [a["id"] for a in ui.vigil.astronaut("eng", day=49)["alerts"]]
    assert ui.bridge.undoText
    ui.bridge.undo()
    assert alert["id"] in [a["id"] for a in ui.vigil.astronaut("eng", day=49)["alerts"]]
    assert ui.bridge.undoText == ""
