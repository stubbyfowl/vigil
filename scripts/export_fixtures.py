"""Save real API responses as fixtures for the frontend smoke tests."""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["VIGIL_DB"] = str(Path(tempfile.mkdtemp()) / "fixtures.db")

from fastapi.testclient import TestClient

from app.main import app
from app.routes.deps import live

DAY = 49
ALERT = "eng-immune-46"
PATHS = [
    "/api/live", "/api/crew", f"/api/astronaut/eng?day={DAY}", f"/api/astronaut/eng/system/immune?day={DAY}",
    f"/api/astronaut/eng/alert/{ALERT}?day={DAY}", f"/api/astronaut/eng/radiation?day={DAY}", f"/api/crew-view?day={DAY}",
    f"/api/ground?day={DAY}", f"/api/astronaut/eng/earth?day={DAY}", "/api/astronaut/eng/share", "/api/timeline",
    "/api/explainer", "/api/results", "/api/about", "/api/admin/config",
]


def main() -> None:
    client = TestClient(app)
    live.set_day(DAY, 0)
    fixtures = {path: client.get(path).json() for path in PATHS}
    target = ROOT / "frontend" / "src" / "test" / "fixtures.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(fixtures))
    print(f"Wrote {len(fixtures)} fixtures, {target.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
