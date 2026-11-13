"""Member accounts: PIN sign-in, roles and lockout. A PIN is stored only as a salted, slow hash."""

import hashlib
import hmac
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import db

ROLES = {
    "commander": "Commander",
    "medical": "Medical Officer",
    "crew": "Crew",
    "ground": "Mission Control",
    "presenter": "Presenter",
}
CREW_ROLES = {"commander", "medical", "crew"}
ITERATIONS = 200_000
LOCK_AFTER_FAILURES = 5
LOCK_SECONDS = 60
MAX_LOCK_SECONDS = 15 * 60
PIN_PATTERN = re.compile(r"\d{4,8}")
NAME_LIMIT = 40
MAX_PRIOR_DOSE = 2000


class AuthError(ValueError):
    """A sign-in or account problem, written so it can be shown as is."""


def hash_pin(pin: str, iterations: int = ITERATIONS) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def pin_matches(pin: str, stored: str) -> bool:
    _, iterations, salt, digest = stored.split("$")
    test = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(test.hex(), digest)


def pin_problem(pin: str) -> str | None:
    """Why a new PIN is not allowed, or None."""
    if not PIN_PATTERN.fullmatch(pin):
        return "A PIN is 4 to 8 digits."
    if len(set(pin)) == 1:
        return "Use more than one digit."
    if pin in "01234567890" or pin in "9876543210":
        return "Avoid a straight run like 1234."
    return None


def initials(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    return "".join(p[0] for p in parts[:3]).upper() or "?"


def public(row: Any, now: float) -> dict[str, Any]:
    """What any screen may know about a member. Never the hash."""
    return {
        "id": row["id"], "name": row["name"], "role": row["role"], "role_name": ROLES[row["role"]], "tag": row["tag"],
        "prior_dose": row["prior_dose"], "active": bool(row["active"]), "must_change": bool(row["must_change"]),
        "locked": row["locked_until"] > now, "locked_seconds": max(0, round(row["locked_until"] - now)),
        "last_sign_in": row["last_sign_in"],
    }


class Accounts:
    """Every account lives in the mission's own database."""

    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self.path, self.clock = path, clock

    def _row(self, member_id: str) -> Any:
        with db.connect(self.path) as con:
            row = con.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        if row is None:
            raise AuthError("No member with that name.")
        return row

    def get(self, member_id: str) -> dict[str, Any]:
        return public(self._row(member_id), self.clock())

    def list(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        order = "CASE role WHEN 'commander' THEN 0 WHEN 'medical' THEN 1 WHEN 'crew' THEN 2 WHEN 'presenter' THEN 3 ELSE 4 END, created_at"
        with db.connect(self.path) as con:
            rows = con.execute(f"SELECT * FROM members {'' if include_inactive else 'WHERE active = 1'} ORDER BY {order}").fetchall()
        now = self.clock()
        return [public(r, now) for r in rows]

    def exists(self) -> bool:
        with db.connect(self.path) as con:
            return con.execute("SELECT COUNT(*) FROM members").fetchone()[0] > 0

    def _new_id(self, name: str) -> str:
        words = [w for w in name.split() if not w.endswith(".")] or name.split()  # skip titles like "Dr."
        base = re.sub(r"[^a-z]", "", words[0].lower()) if words else ""
        base = base or "member"
        with db.connect(self.path) as con:
            taken = {r[0] for r in con.execute("SELECT id FROM members")}
        candidate, n = base, 2
        while candidate in taken:
            candidate, n = f"{base}{n}", n + 1
        return candidate

    def _check_name(self, name: str, member_id: str | None = None) -> None:
        """Two accounts with one name would be impossible to tell apart on the sign-in screen and at Mission Control."""
        with db.connect(self.path) as con:
            rows = con.execute("SELECT id, name FROM members").fetchall()
        if any(r[1].casefold() == name.casefold() and r[0] != member_id for r in rows):
            raise AuthError(f"{name} has an account already. Add a middle initial to tell the two apart.")

    def _free_tag(self, name: str, member_id: str | None = None) -> str:
        """Initials, with a number added when two people share them, like LN and LN2."""
        base = initials(name)
        with db.connect(self.path) as con:
            taken = {r[0] for r in con.execute("SELECT tag FROM members WHERE id != ?", (member_id or "",))}
        tag, n = base, 2
        while tag in taken:
            tag, n = f"{base}{n}", n + 1
        return tag

    def create(
        self, name: str, role: str, pin: str, prior_dose: float = 0.0, must_change: bool = True,
        member_id: str | None = None, tag: str | None = None, iterations: int = ITERATIONS, check_pin: bool = True,
    ) -> dict[str, Any]:
        name = " ".join(name.split())
        if not name or len(name) > NAME_LIMIT:
            raise AuthError(f"Enter a name of 1 to {NAME_LIMIT} characters.")
        if role not in ROLES:
            raise AuthError("Choose a role.")
        if not isinstance(prior_dose, int | float) or not 0 <= prior_dose <= MAX_PRIOR_DOSE:
            raise AuthError(f"Career dose before this mission must be 0 to {MAX_PRIOR_DOSE} mSv.")
        problem = pin_problem(pin) if check_pin else None
        if problem:
            raise AuthError(problem)
        self._check_name(name)
        tag = tag or self._free_tag(name)
        member_id = member_id or self._new_id(name)
        with db.connect(self.path) as con:
            con.execute(
                "INSERT INTO members (id, name, role, tag, prior_dose, pin_hash, must_change, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (member_id, name, role, tag, float(prior_dose), hash_pin(pin, iterations), int(must_change), self.clock()),
            )
        return self.get(member_id)

    def sign_in(self, member_id: str, pin: str) -> dict[str, Any]:
        """Check a PIN. Repeated misses lock the account for longer each time."""
        row = self._row(member_id)
        now = self.clock()
        if not row["active"]:
            raise AuthError("This account is turned off. Ask the Commander.")
        if row["locked_until"] > now:
            raise AuthError(f"Locked after too many wrong PINs. Try again in {max(1, round(row['locked_until'] - now))} seconds.")
        if not pin_matches(pin, row["pin_hash"]):
            failed = row["failed"] + 1
            seconds = min(LOCK_SECONDS * 2 ** row["lockouts"], MAX_LOCK_SECONDS)
            with db.connect(self.path) as con:  # commit before raising, or the miss would not count
                if failed >= LOCK_AFTER_FAILURES:
                    con.execute("UPDATE members SET failed = 0, lockouts = lockouts + 1, locked_until = ? WHERE id = ?", (now + seconds, member_id))
                else:
                    con.execute("UPDATE members SET failed = ? WHERE id = ?", (failed, member_id))
            if failed >= LOCK_AFTER_FAILURES:
                raise AuthError(f"Wrong PIN. Locked for {seconds} seconds.")
            left = LOCK_AFTER_FAILURES - failed
            raise AuthError(f"Wrong PIN. {left} {'try' if left == 1 else 'tries'} left before a short lock.")
        with db.connect(self.path) as con:
            con.execute("UPDATE members SET failed = 0, lockouts = 0, locked_until = 0, last_sign_in = ? WHERE id = ?", (now, member_id))
        return public(row, now) | {"previous_sign_in": row["last_sign_in"]}

    def change_pin(self, member_id: str, old: str, new: str) -> None:
        self.sign_in(member_id, old)
        self.set_pin(member_id, new, must_change=False)

    def set_pin(self, member_id: str, new: str, must_change: bool) -> None:
        problem = pin_problem(new)
        if problem:
            raise AuthError(problem)
        self._row(member_id)
        with db.connect(self.path) as con:
            con.execute(
                "UPDATE members SET pin_hash = ?, must_change = ?, failed = 0, lockouts = 0, locked_until = 0 WHERE id = ?",
                (hash_pin(new), int(must_change), member_id),
            )

    def unlock(self, member_id: str) -> None:
        self._row(member_id)
        with db.connect(self.path) as con:
            con.execute("UPDATE members SET failed = 0, lockouts = 0, locked_until = 0 WHERE id = ?", (member_id,))

    def _commanders_left(self, excluding: str) -> int:
        with db.connect(self.path) as con:
            return con.execute("SELECT COUNT(*) FROM members WHERE role = 'commander' AND active = 1 AND id != ?", (excluding,)).fetchone()[0]

    def update(self, member_id: str, name: str | None = None, role: str | None = None,
               prior_dose: float | None = None, active: bool | None = None) -> dict[str, Any]:
        row = self._row(member_id)
        losing_command = row["role"] == "commander" and ((role is not None and role != "commander") or active is False)
        if losing_command and self._commanders_left(member_id) == 0:
            raise AuthError("A mission needs at least one active Commander.")
        if name is not None:
            name = " ".join(name.split())
            if not name or len(name) > NAME_LIMIT:
                raise AuthError(f"Enter a name of 1 to {NAME_LIMIT} characters.")
            self._check_name(name, member_id)
        if role is not None and role not in ROLES:
            raise AuthError("Choose a role.")
        if prior_dose is not None and not 0 <= prior_dose <= MAX_PRIOR_DOSE:
            raise AuthError(f"Career dose before this mission must be 0 to {MAX_PRIOR_DOSE} mSv.")
        changes = {"name": name, "tag": self._free_tag(name, member_id) if name else None, "role": role, "prior_dose": prior_dose,
                   "active": None if active is None else int(active)}
        sets = {k: v for k, v in changes.items() if v is not None}
        if sets:
            with db.connect(self.path) as con:
                con.execute(f"UPDATE members SET {', '.join(f'{k} = ?' for k in sets)} WHERE id = ?", (*sets.values(), member_id))
        return self.get(member_id)
