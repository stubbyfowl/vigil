"""SQLite storage: members, readings, check-ins, alert actions, share choices, packets and the audit log."""

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
  seed INTEGER, astronaut TEXT, day INTEGER, signal TEXT, value REAL,
  PRIMARY KEY (seed, astronaut, day, signal));
CREATE TABLE IF NOT EXISTS checkins (
  astronaut TEXT, day INTEGER, mood INTEGER, sleep_quality INTEGER, energy INTEGER,
  stress INTEGER, symptoms INTEGER, journal_score REAL, journal_text TEXT,
  PRIMARY KEY (astronaut, day));
CREATE TABLE IF NOT EXISTS food_log (
  astronaut TEXT, day INTEGER, fiber INTEGER, processed INTEGER,
  PRIMARY KEY (astronaut, day));
CREATE TABLE IF NOT EXISTS alert_actions (
  alert_id TEXT, day INTEGER, action TEXT, level INTEGER);
CREATE TABLE IF NOT EXISTS share_prefs (
  astronaut TEXT PRIMARY KEY, share_crew INTEGER DEFAULT 0, share_ground INTEGER DEFAULT 0,
  keep_journal_text INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS members (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL, tag TEXT NOT NULL,
  prior_dose REAL DEFAULT 0, pin_hash TEXT NOT NULL, active INTEGER DEFAULT 1,
  must_change INTEGER DEFAULT 0, failed INTEGER DEFAULT 0, lockouts INTEGER DEFAULT 0,
  locked_until REAL DEFAULT 0, created_at REAL, last_sign_in REAL);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY, member TEXT NOT NULL, signal TEXT NOT NULL, value REAL NOT NULL,
  day INTEGER NOT NULL, source TEXT NOT NULL, entered_by TEXT, created_at REAL);
CREATE INDEX IF NOT EXISTS entries_by_member ON entries (member, day);
CREATE TABLE IF NOT EXISTS packets (
  id INTEGER PRIMARY KEY, ref TEXT UNIQUE, kind TEXT, member TEXT, title TEXT, priority INTEGER,
  size_kb REAL, day INTEGER, payload TEXT, created_at REAL, file TEXT);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY, at REAL, actor TEXT, action TEXT, target TEXT, detail TEXT);
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


def get_setting(path: Path, key: str, default: Any = None) -> Any:
    with connect(path) as con:
        row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_setting(path: Path, key: str, value: Any) -> None:
    with connect(path) as con:
        con.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, json.dumps(value)))


def audit(path: Path, actor: str, action: str, target: str = "", detail: str = "") -> None:
    """Record who did what. Never store PINs, readings or journal text here."""
    with connect(path) as con:
        con.execute("INSERT INTO audit (at, actor, action, target, detail) VALUES (?,?,?,?,?)", (time.time(), actor, action, target, detail))


def audit_log(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    with connect(path) as con:
        rows = con.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def backup(path: Path, folder: Path, stamp: str) -> Path:
    """Copy the database safely while it is open, using SQLite's own backup."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{path.stem}-{stamp}.db"
    with connect(path) as source:
        copy = sqlite3.connect(target)
        try:
            source.backup(copy)
        finally:
            copy.close()
    return target
