"""Point the app at a throwaway home folder before anything imports it."""

import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
tmp = Path(tempfile.mkdtemp(prefix="vigil-test-"))
shutil.copy(ROOT / "config" / "thresholds.yaml", tmp / "thresholds.yaml")
os.environ["VIGIL_HOME"] = str(tmp)
os.environ["VIGIL_THRESHOLDS"] = str(tmp / "thresholds.yaml")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
