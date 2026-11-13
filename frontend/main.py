"""Vigil desktop application. Runs on Linux, macOS and Windows."""

import argparse
import signal
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "frontend"))

import shiboken6  # noqa: E402
from app import config  # noqa: E402
from app.views import DEMO_PIN, Vigil  # noqa: E402
from bridge import Bridge  # noqa: E402
from PySide6.QtCore import QObject, QTimer  # noqa: E402
from PySide6.QtGui import QFontDatabase, QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402

CHECK_MS = 1500
# Every screen the --check run opens, so a missing data file or a broken screen fails the check.
CHECK_ROUTES = (
    "/", "/checkin", "/radiation", "/crew", "/ground", "/earth", "/sensors", "/timeline", "/explainer",
    "/delay", "/results", "/about", "/admin", "/profile", "/accounts", "/audit", "/system/heart",
    "/chat", "/replay", "/album", "/gut",
)


def check_screens(app: QGuiApplication, vigil: Vigil, bridge: Bridge) -> list[str]:
    """Open every screen as the Presenter and report any request that failed for a reason other than access."""
    found: list[str] = []
    if vigil.mode != "demo":
        return found  # a real mission's accounts are not ours to sign in to
    real = vigil.request

    def request(session, name, args):  # type: ignore[no-untyped-def]
        try:
            return real(session, name, args)
        except PermissionError:
            raise
        except Exception as err:
            found.append(f"{name}: {type(err).__name__}: {err}")
            raise

    vigil.request = request  # type: ignore[method-assign]
    bridge.signIn("presenter", DEMO_PIN)
    for route in CHECK_ROUTES:
        bridge.navigate(route)
        app.processEvents()
    bridge.signOut()
    vigil.request = real  # type: ignore[method-assign]
    return found


def quick_window(obj: QObject) -> QQuickWindow:
    """Python sees the QML root as a plain window. This gives access to its scene."""
    return shiboken6.wrapInstance(shiboken6.getCppPointer(obj)[0], QQuickWindow)


def create_engine(app: QGuiApplication, vigil: Vigil, on_warning: Callable | None = None) -> tuple[QQmlApplicationEngine, Bridge]:
    """Load the fonts and the interface. Fonts ship with the app, so nothing comes from a network."""
    for font in sorted((config.FRONTEND_DIR / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font))
    bridge = Bridge(vigil, app)
    qml = config.FRONTEND_DIR / "qml"

    def load(file: str, force_theme: str, station: Bridge) -> QQmlApplicationEngine:
        engine = QQmlApplicationEngine()
        if on_warning:
            engine.warnings.connect(on_warning)
        engine.rootContext().setContextProperty("vigil", station)
        engine.rootContext().setContextProperty("forceTheme", force_theme)
        engine.load(str(qml / file))
        return engine

    # Mission Control gets its own engine and its own sign-in, and stays dark whatever theme the tablet uses.
    ground: list[QQmlApplicationEngine] = []

    def open_ground() -> None:
        if ground:
            # It may have been closed (hidden) or be behind the main window: show it and bring it forward.
            window = quick_window(ground[0].rootObjects()[0])
            window.show()
            window.raise_()
            window.requestActivate()
        else:
            station = Bridge(vigil, app, station="ground")
            ground.append(load("GroundWindow.qml", "dark", station))
            bridge.ground_bridge = station

    bridge.open_ground_window = open_ground
    return load("Main.qml", "", bridge), bridge


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="play the Demo Director on launch")
    parser.add_argument("--kiosk", action="store_true", help="run fullscreen, for a dedicated panel")
    parser.add_argument("--ground", action="store_true", help="also open the Mission Control window")
    parser.add_argument("--check", action="store_true", help="load every part of the interface, report problems, and exit")
    args, qt_args = parser.parse_known_args()

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QGuiApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Vigil")
    app.setOrganizationName("Vigil")
    # A real mission opens if this computer has one. Otherwise the demo, with a first-run choice.
    vigil = Vigil(mode="demo" if args.demo or not Vigil.mission_exists() else "live")
    problems: list[str] = []
    engine, bridge = create_engine(app, vigil, lambda found: problems.extend(w.toString() for w in found))
    app.aboutToQuit.connect(bridge.stop_sound)
    if not engine.rootObjects():
        print("\n".join(problems), file=sys.stderr)
        return 1
    root = engine.rootObjects()[0]
    root.setProperty("kiosk", args.kiosk)
    if args.ground:
        bridge.openGround()
    if args.demo:
        bridge.signIn("presenter", DEMO_PIN)
        if args.ground:
            bridge.ground_bridge.signIn("presenter", DEMO_PIN)
        bridge.ask("demo_start", "{}")
    bridge.tick()
    if args.check:
        problems.extend(check_screens(app, vigil, bridge))
        QTimer.singleShot(CHECK_MS, app.quit)
        app.exec()
        print("\n".join(problems) or "Vigil check passed.")
        return 1 if problems else 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
