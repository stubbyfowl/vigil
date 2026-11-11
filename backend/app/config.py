"""Paths and the editable thresholds file."""

import os
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

FROZEN = getattr(sys, "frozen", False)  # True inside a packaged build
ROOT = Path(getattr(sys, "_MEIPASS")) if FROZEN else Path(__file__).resolve().parents[2]  # noqa: B009
DATA_DIR = ROOT / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
FRONTEND_DIR = ROOT / "frontend"
# Packaged builds are read-only, so anything the astronaut changes lives in a per-user folder.
HOME = Path(os.environ.get("VIGIL_HOME", Path.home() / ".local" / "share" / "vigil" if FROZEN else DATA_DIR))
DEFAULTS_PATH = ROOT / "config" / "thresholds.defaults.yaml"
THRESHOLDS_PATH = Path(os.environ.get("VIGIL_THRESHOLDS", HOME / "thresholds.yaml" if FROZEN else ROOT / "config" / "thresholds.yaml"))
DB_PATH = Path(os.environ.get("VIGIL_DB", HOME / "vigil.db"))  # the demo mission
MISSION_DB_PATH = Path(os.environ.get("VIGIL_MISSION_DB", HOME / "mission.db"))  # a real mission
PREFS_PATH = HOME / "ui.json"
# Folders a live mission reads and writes. The vehicle's comm system drains the outbox.
OUTBOX_DIR = HOME / "outbox"
IMPORT_DIR = HOME / "import"
EXPORT_DIR = HOME / "exports"
BACKUP_DIR = HOME / "backups"
HEADER = "# A flight surgeon has not reviewed these values. Edit here or on the Thresholds screen.\n"

Config = dict[str, Any]


def load_config() -> Config:
    """Read thresholds.yaml, creating it from the defaults on first run."""
    if not THRESHOLDS_PATH.exists():
        THRESHOLDS_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(DEFAULTS_PATH, THRESHOLDS_PATH)
    with THRESHOLDS_PATH.open() as f:
        loaded: Config = yaml.safe_load(f)
    return loaded


def save_config(cfg: Config) -> None:
    """Write thresholds.yaml, keeping the safety header."""
    THRESHOLDS_PATH.write_text(HEADER + yaml.safe_dump(cfg, sort_keys=False))
