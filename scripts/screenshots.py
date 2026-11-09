"""Render every screen at 1280x800 to docs/screens, with no display needed."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "frontend")]
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("VIGIL_HOME", tempfile.mkdtemp())
os.environ.setdefault("VIGIL_THRESHOLDS", str(ROOT / "config" / "thresholds.yaml"))

from app.views import Vigil
from main import create_engine, quick_window
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

SHOTS = [
    ("home", "/", 49, "eng"), ("home-clear", "/", 30, "ctl"), ("alert", "/alert/eng-immune-46", 49, "eng"), ("system", "/system/immune", 49, "eng"),
    ("checkin", "/checkin", 49, "eng"), ("radiation", "/radiation", 120, "eng"), ("crew", "/crew", 96, "eng"), ("ground", "/ground", 120, "eng"),
    ("earth", "/earth", 49, "eng"), ("sensors", "/sensors", 49, "eng"), ("timeline", "/timeline", 96, "eng"), ("explainer", "/explainer", 176, "eng"),
    ("delay", "/delay", 49, "eng"), ("results", "/results", 176, "eng"), ("about", "/about", 49, "eng"), ("admin", "/admin", 49, "eng"),
]


def main() -> None:
    target = ROOT / "docs" / "screens"
    target.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    app = QGuiApplication([])
    vigil = Vigil()
    problems: list[str] = []
    engine, bridge = create_engine(app, vigil, lambda w: problems.extend(x.toString() for x in w))
    window = quick_window(engine.rootObjects()[0])
    bridge.acknowledgeWelcome()
    QTest.qWait(300)
    for name, route, day, who in SHOTS:
        if only and name not in only:
            continue
        vigil.set_clock(day=day, running=False)
        bridge.astronaut = who
        bridge.tick()
        bridge.navigate(route)
        QTest.qWait(450)
        window.grabWindow().save(str(target / f"{name}.png"))
    print("\n".join(problems) or f"Rendered {len(only) or len(SHOTS)} screens to {target}")


if __name__ == "__main__":
    main()
