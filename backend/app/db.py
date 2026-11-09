"""SQLite storage for readings, check-ins, alert actions and share choices."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
  seed INTEGER, astronaut TEXT, day INTEGER, signal TEXT, value REAL,
  PRIMARY KEY (seed, astronaut, day, signal));
CREATE TABLE IF NOT EXISTS checkins (
  astronaut TEXT, day INTEGER, mood INTEGER, sleep_quality INTEGER, energy INTEGER,
  stress INTEGER, symptoms INTEGER, journal_score REAL, journal_text TEXT,
  PRIMARY KEY (astronaut, day));
CREATE TABLE IF NOT EXISTS alert_actions (
  alert_id TEXT, day INTEGER, action TEXT, level INTEGER);
CREATE TABLE IF NOT EXISTS share_prefs (
  astronaut TEXT PRIMARY KEY, share_crew INTEGER DEFAULT 0, share_ground INTEGER DEFAULT 0,
  keep_journal_text INTEGER DEFAULT 0);
"""


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open the database, create tables if needed, and commit on success."""
    target = path or config.DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(target)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()
