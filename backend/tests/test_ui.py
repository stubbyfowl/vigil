"""Load the real interface offscreen. Every screen must render with no QML errors."""

import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "frontend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.views import DEMO_PIN, Vigil  # noqa: E402
from main import create_engine, quick_window  # noqa: E402

TARGETS = ("QQuickAbstractButton", "QQuickTextField", "QQuickSlider", "QQuickTextArea")
ROUTES = [
    "/", "/alert/eng-immune-46", "/system/immune", "/checkin", "/radiation", "/crew", "/ground", "/earth", "/sensors",
    "/timeline", "/explainer", "/delay", "/results", "/about", "/admin", "/profile", "/accounts", "/audit",
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
    assert built.bridge.signIn("presenter", DEMO_PIN) == ""
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
    def ground_windows():  # other test modules may have their own in this process
        return {w for w in ui.app.topLevelWindows() if w.title() == "Vigil Mission Control"}
    ui.warnings.clear()
    before = ground_windows()
    ui.bridge.openGround()
    QTest.qWait(200)
    (window,) = ground_windows() - before
    assert window.isVisible()
    window.close()  # closing only hides it, so the menu item must bring it back
    ui.bridge.openGround()
    QTest.qWait(100)
    assert ground_windows() - before == {window} and window.isVisible()
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


def screen_item(ui, route, day=49):
    ui.show(route, day)
    return ui.window.findChild(QObject, "page").property("item")


def call(obj, method, *args):
    QMetaObject.invokeMethod(obj, method, Qt.DirectConnection, *[Q_ARG("QVariant", a) for a in args])


def test_checkin_saves_through_the_screen(ui):
    ui.warnings.clear()
    screen = screen_item(ui, "/checkin")
    for key, value in (("mood", 7), ("sleep_quality", 6), ("energy", 7), ("stress", 3), ("symptoms", 0)):
        call(screen, "choose", key, value)
    call(screen, "save")
    QTest.qWait(100)
    assert screen.property("saved") is not None
    assert ui.warnings == []
    ui.vigil.store.reset_interactive()
    ui.bridge.tick()


def test_alert_buttons_and_why_drawer(ui):
    ui.warnings.clear()
    ui.vigil.store.reset_interactive()
    ui.bridge.navigate("/")
    screen = screen_item(ui, "/alert/eng-immune-46")
    screen.setProperty("showWhy", True)
    QTest.qWait(250)
    call(screen, "act", "snooze")
    QTest.qWait(100)
    assert ui.bridge.route == "/"
    assert ui.bridge.undoText
    ui.bridge.undo()
    assert ui.warnings == []


def test_call_earth_from_the_screen(ui):
    ui.warnings.clear()
    screen = screen_item(ui, "/earth")
    call(screen, "send")
    QTest.qWait(50)
    assert screen.property("sent") is True
    assert ui.warnings == []


def test_delay_theater_runs_both_paths(ui):
    ui.warnings.clear()
    screen = screen_item(ui, "/delay")
    call(screen, "start", "vigil")
    QTest.qWait(1700)
    assert screen.property("steps") == 5
    call(screen, "start", "waiting")
    QTest.qWait(300)
    assert screen.property("minutes") > 0
    assert ui.warnings == []


def test_storm_drill_opens(ui):
    ui.warnings.clear()
    screen = screen_item(ui, "/radiation", day=60)
    screen.setProperty("drill", True)
    QTest.qWait(300)
    assert any("Stop your task" in str(i.property("text")) for i in ui.items())
    assert ui.warnings == []


def test_admin_saves_and_restores(ui):
    ui.warnings.clear()
    screen = screen_item(ui, "/admin")
    call(screen, "save")
    assert "Saved" in screen.property("message")
    call(screen, "restore")
    QTest.qWait(100)
    assert "restored" in screen.property("message")
    assert ui.warnings == []


def small_targets(ui):
    return [
        (i.metaObject().className(), round(i.width()), round(i.height()))
        for i in ui.items() if isinstance(i, QQuickItem) and any(i.inherits(t) for t in TARGETS) and (i.width() < 55.5 or i.height() < 55.5)
    ]


def find_named(ui, name):
    return next((i for i in ui.items() if i.objectName() == name), None)


def test_sign_in_screen_renders_and_refuses_a_wrong_pin(ui):
    ui.warnings.clear()
    ui.bridge.signOut()
    QTest.qWait(150)
    assert ui.bridge.stage in ("signin", "welcome")
    if ui.bridge.stage == "welcome":
        ui.bridge.chooseDemo()
        QTest.qWait(150)
    assert find_named(ui, "signin") is not None
    assert small_targets(ui) == []
    assert "Wrong PIN" in ui.bridge.signIn("eng", "9999")
    assert ui.bridge.signIn("presenter", DEMO_PIN) == ""
    assert ui.bridge.stage == "app"
    assert ui.warnings == []


def test_lock_hides_everything_until_the_pin(ui):
    ui.warnings.clear()
    ui.show("/")
    ui.bridge.lock()
    QTest.qWait(150)
    assert ui.bridge.locked and find_named(ui, "lock") is not None
    assert "error" in ui.bridge.ask("astronaut", "{}")
    assert small_targets(ui) == []
    assert ui.bridge.unlock("0000") != ""
    assert ui.bridge.unlock(DEMO_PIN) == ""
    assert not ui.bridge.locked
    assert ui.warnings == []


def test_crew_member_sees_only_their_own_data(ui):
    ui.bridge.signOut()
    assert ui.bridge.signIn("eng", DEMO_PIN) == ""
    assert ui.bridge.astronaut == "eng"
    ui.bridge.astronaut = "cmdr"  # ignored for crew members
    assert ui.bridge.astronaut == "eng"
    assert "only open your own" in ui.bridge.ask("astronaut", '{"id": "cmdr"}')
    ui.warnings.clear()
    ui.show("/")
    ui.show("/profile")
    assert ui.warnings == []
    ui.bridge.signOut()
    assert ui.bridge.signIn("presenter", DEMO_PIN) == ""


@pytest.mark.parametrize("stage", ["welcome", "setup"])
def test_first_run_stages_render(ui, stage):
    ui.warnings.clear()
    ui.bridge.signOut()
    ui.bridge._set_stage(stage)
    QTest.qWait(150)
    assert find_named(ui, stage + "Stage") is not None
    assert small_targets(ui) == []
    assert ui.warnings == []
    ui.bridge._set_stage("signin")
    assert ui.bridge.signIn("presenter", DEMO_PIN) == ""


def tile_note(ui, member):
    """The line under a name on the sign-in screen."""
    name = ui.vigil.accounts.get(member)["name"]
    tile = next(i for i in ui.items() if i.property("text") == name)
    texts = [c.property("text") for c in tile.parentItem().childItems() if isinstance(c.property("text"), str)]
    return next(t for t in texts if t != name)


def test_sign_out_from_the_lock_screen_and_live_lockout_countdown(ui):
    ui.bridge.signOut()
    if ui.bridge.stage == "welcome":
        ui.bridge.chooseDemo()  # with no real mission yet, signing out returns to the first-run choice
    assert ui.bridge.signIn("presenter", DEMO_PIN) == ""
    ui.show("/")
    ui.bridge.lock()
    QTest.qWait(100)
    ui.warnings.clear()
    ui.bridge.signOut()
    QTest.qWait(200)
    texts = [i.property("text") for i in ui.items() if isinstance(i.property("text"), str)]
    assert any("Day 49 / " in t for t in texts) and not any("undefined" in t for t in texts)
    screen = find_named(ui, "signin")
    for _ in range(5):
        ui.bridge.signIn("plt", "9999")
    screen.setProperty("refresh", screen.property("refresh") + 1)  # what the PIN pad does after each try
    QTest.qWait(150)
    first = tile_note(ui, "plt")
    assert first.startswith("Locked · opens in ")
    QTest.qWait(2100)
    assert tile_note(ui, "plt") != first  # counts down on its own, with nobody touching the screen
    ui.vigil.accounts.unlock("plt")
    assert ui.warnings == []
    assert ui.bridge.signIn("presenter", DEMO_PIN) == ""


def test_system_arrows_follow_any_hidden_card(ui):
    home = screen_item(ui, "/")
    cards = home.findChild(QObject, "cards")
    arrows = {i.property("text"): i for i in ui.items() if i.inherits("QQuickAbstractButton") and i.property("text") in ("‹", "›")}
    cards.setProperty("contentX", 0)
    assert not arrows["‹"].property("enabled") and arrows["›"].property("enabled")
    cards.setProperty("contentX", 20)  # a sliver of the first card is hidden
    assert arrows["‹"].property("enabled")
    QTest.mouseClick(ui.window, Qt.LeftButton, pos=arrows["‹"].mapToScene(arrows["‹"].boundingRect().center()).toPoint())
    QTest.qWait(50)
    assert cards.property("contentX") == 0


def test_small_window_scrolls_home_and_the_menu(ui):
    ui.bridge.signOut()
    assert ui.bridge.signIn("cmdr", DEMO_PIN) == ""
    old = ui.window.size()
    ui.window.resize(1024, 700)
    home = screen_item(ui, "/")
    flick = next(i for i in ui.items(home) if i.inherits("QQuickFlickable") and not i.objectName())
    assert flick.property("contentHeight") >= flick.height()
    menu = ui.window.findChild(QObject, "menu")
    menu.setProperty("visible", True)
    QTest.qWait(300)
    assert menu.property("y") + menu.property("height") <= 700
    menu.setProperty("visible", False)
    ui.window.resize(old)
    ui.bridge.signOut()
    assert ui.bridge.signIn("presenter", DEMO_PIN) == ""


def test_journal_scrolls_when_the_words_outgrow_the_box(ui):
    screen = screen_item(ui, "/checkin")
    journal = screen.findChild(QObject, "journal")
    journal.setProperty("text", "A long day. " * 120)
    QTest.qWait(100)
    box = journal.parentItem().parentItem()  # the scroll view around it
    assert journal.height() > box.height()
    journal.setProperty("text", "")
