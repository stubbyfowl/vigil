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

import random
from datetime import date, timedelta

from app.views import DEMO_PIN, Vigil
from main import create_engine, quick_window
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

SHOTS = [
    ("home", "/", 49, "eng"), ("home-clear", "/", 30, "ctl"), ("alert", "/alert/eng-immune-46", 49, "eng"), ("system", "/system/immune", 49, "eng"),
    ("checkin", "/checkin", 49, "eng"), ("radiation", "/radiation", 120, "eng"), ("crew", "/crew", 96, "eng"), ("ground", "/ground", 120, "eng"),
    ("earth", "/earth", 49, "eng"), ("sensors", "/sensors", 49, "eng"), ("timeline", "/timeline", 96, "eng"), ("explainer", "/explainer", 176, "eng"),
    ("delay", "/delay", 49, "eng"), ("results", "/results", 176, "eng"), ("about", "/about", 49, "eng"), ("admin", "/admin", 49, "eng"),
    ("profile", "/profile", 49, "eng"), ("accounts", "/accounts", 49, "eng"), ("audit", "/audit", 49, "eng"),
    ("chat", "/chat", 49, "eng"), ("replay", "/replay", 60, "eng"), ("album", "/album", 70, "cmdr"), ("gut", "/gut", 49, "eng"),
]
# A real mission, seen by each role: (file, member, PIN, route)
LIVE_SHOTS = [
    ("live-home", "lena", "5170", "/"), ("live-log", "lena", "5170", "/log"), ("live-sources", "lena", "5170", "/sensors"),
    ("live-mo-home", "priya", "7391", "/"), ("live-accounts", "ana", "4826", "/accounts"), ("live-audit", "ana", "4826", "/audit"),
]


def build_live_mission(vigil: Vigil, today: list[date]) -> None:
    """Fifteen days of entries, ending today. Lena's heart rate climbs in the last few days."""
    start = date.today() - timedelta(days=14)
    today[0] = start
    vigil.setup_mission("Analog 1", start.isoformat(), 180, "Ana Reyes", "4826", 190)
    boss = {"id": "ana", "role": "commander"}
    for name, role, pin in (("Priya Nair", "medical", "7391"), ("Lena Novak", "crew", "5170"), ("Dr. Okafor", "ground", "8402")):
        vigil.request(boss, "add_member", {"name": name, "role": role, "pin": pin})
    for member, pin in (("priya", "7391"), ("lena", "5170"), ("okafor", "8402")):
        vigil.accounts.set_pin(member, pin, must_change=False)
    rng = random.Random(3)
    for i in range(15):
        today[0] = start + timedelta(days=i)
        vigil.live.tick(0)
        for who, rise in (("lena", 9 if i >= 11 else 0), ("priya", 0), ("ana", 0)):
            me = {"id": who, "role": "crew"}
            vigil.request(me, "log_readings", {"values": {
                "resting_hr": round(60 + rng.gauss(0, 1.5) + rise, 1), "hrv": round(58 + rng.gauss(0, 4) - 2 * rise, 1),
                "bp_sys": round(116 + rng.gauss(0, 3)), "temp": 36.7, "sleep_hours": round(7 + rng.gauss(0, 0.3), 1), "dose_rate": 80,
            }})
            if i < 14 or who != "lena":
                vigil.request(me, "checkin", {"mood": 7, "sleep_quality": 7, "energy": 7, "stress": 3, "symptoms": 0})
    vigil.request({"id": "lena", "role": "crew"}, "call_earth", {"note": "Heart rate feels high"})


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
    bridge.signIn("presenter", DEMO_PIN)

    def engine_ground(station):  # the Mission Control window is the newest top-level window
        return [w for w in app.topLevelWindows() if w.title() == "Vigil Mission Control"][0]
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
    def shoot(name: str, wait: int = 450) -> None:
        if not only or name in only:
            QTest.qWait(wait)
            window.grabWindow().save(str(target / f"{name}.png"))

    bridge.lock()
    shoot("lock")
    bridge.signOut()
    shoot("welcome")
    bridge.chooseDemo()
    shoot("signin")
    for stage in ("setup",):
        bridge._set_stage(stage)
        shoot(stage)

    today = [date.today()]
    vigil.today = lambda: today[0]
    build_live_mission(vigil, today)
    bridge.openMission("live")
    shoot("live-signin")
    for name, member, pin, route in LIVE_SHOTS:
        bridge.signOut()
        bridge.signIn(member, pin)
        bridge.acknowledgeWelcome()
        bridge.navigate(route)
        shoot(name)
    bridge.signOut()
    bridge.openGround()
    station = bridge.ground_bridge
    station.signIn("okafor", "8402")
    QTest.qWait(450)
    if not only or "live-ground" in only:
        quick_window(engine_ground(station)).grabWindow().save(str(target / "live-ground.png"))
    print("\n".join(problems) or f"Rendered screens to {target}")


if __name__ == "__main__":
    main()
