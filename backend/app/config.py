"""Paths and the editable thresholds file."""

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
THRESHOLDS_PATH = Path(os.environ.get("VIGIL_THRESHOLDS", ROOT / "config" / "thresholds.yaml"))
DB_PATH = Path(os.environ.get("VIGIL_DB", DATA_DIR / "vigil.db"))
FRONTEND_DIST = ROOT / "frontend" / "dist"
HEADER = "# Starting values, not clinical limits. Edit here or on the Admin screen.\n"

Config = dict[str, Any]


def load_config() -> Config:
    """Read thresholds.yaml."""
    with THRESHOLDS_PATH.open() as f:
        loaded: Config = yaml.safe_load(f)
    return loaded


def save_config(cfg: Config) -> None:
    """Write thresholds.yaml, keeping the safety header."""
    THRESHOLDS_PATH.write_text(HEADER + yaml.safe_dump(cfg, sort_keys=False))
