"""Point the app at a throwaway database and config before anything imports it."""

import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
tmp = Path(tempfile.mkdtemp(prefix="vigil-test-"))
for name in ("thresholds.yaml", "thresholds.defaults.yaml"):
    shutil.copy(ROOT / "config" / name, tmp / name)
os.environ["VIGIL_DB"] = str(tmp / "test.db")
os.environ["VIGIL_THRESHOLDS"] = str(tmp / "thresholds.yaml")
