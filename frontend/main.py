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
from app.views import Vigil  # noqa: E402
from bridge import Bridge  # noqa: E402
from PySide6.QtCore import QObject  # noqa: E402
from PySide6.QtGui import QFontDatabase, QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402


def quick_window(obj: QObject) -> QQuickWindow:
    """Python sees the QML root as a plain window. This gives access to its scene."""
    return shiboken6.wrapInstance(shiboken6.getCppPointer(obj)[0], QQuickWindow)


def create_engine(app: QGuiApplication, vigil: Vigil, on_warning: Callable | None = None) -> tuple[QQmlApplicationEngine, Bridge]:
    """Load the fonts and the interface. Fonts ship with the app, so nothing comes from a network."""
    for font in sorted((config.FRONTEND_DIR / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(font))
    bridge = Bridge(vigil, app)
    engine = QQmlApplicationEngine()
    if on_warning:
        engine.warnings.connect(on_warning)
    engine.rootContext().setContextProperty("vigil", bridge)
    engine.load(str(config.FRONTEND_DIR / "qml" / "Main.qml"))
    return engine, bridge


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="play the Demo Director on launch")
    parser.add_argument("--kiosk", action="store_true", help="run fullscreen, for a dedicated panel")
    parser.add_argument("--ground", action="store_true", help="also open the Mission Control window")
    args, qt_args = parser.parse_known_args()

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QGuiApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Vigil")
    app.setOrganizationName("Vigil")
    vigil = Vigil()
    engine, bridge = create_engine(app, vigil)
    if not engine.rootObjects():
        return 1
    root = engine.rootObjects()[0]
    root.setProperty("kiosk", args.kiosk)
    root.setProperty("groundOpen", args.ground)
    if args.demo:
        vigil.demo_start()
    bridge.tick()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
