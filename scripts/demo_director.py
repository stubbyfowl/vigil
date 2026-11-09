"""Open Vigil and play the two-minute Demo Director. Add --ground for a second window."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(ROOT / "frontend" / "main.py"), "--demo", *sys.argv[1:]]))
