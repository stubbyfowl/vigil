import sqlite3

import pytest
from app import auth
from app.auth import Accounts, AuthError

FAST = 1000  # hashing iterations for tests only


@pytest.fixture
def accounts(tmp_path):
    clock = [1000.0]
    acc = Accounts(tmp_path / "m.db", lambda: clock[0])
    acc.clock_value = clock
    acc.create("Ana Reyes", "commander", "4826", 190, must_change=False, iterations=FAST)
    acc.create("Lena Novak", "crew", "5170", iterations=FAST)
    return acc


def test_pins_are_never_stored_as_typed(accounts, tmp_path):
    raw = sqlite3.connect(tmp_path / "m.db").execute("SELECT pin_hash FROM members").fetchall()
    assert all(h.startswith("pbkdf2_sha256$") and "4826" not in h and "5170" not in h for (h,) in raw)


def test_same_pin_hashes_differently():
    assert auth.hash_pin("4826", FAST) != auth.hash_pin("4826", FAST)


@pytest.mark.parametrize("pin, ok", [("4826", True), ("123", False), ("1234", False), ("9876", False), ("7777", False), ("12a4", False), ("482617", True)])
def test_pin_rules(pin, ok):
    assert (auth.pin_problem(pin) is None) == ok


def test_sign_in_and_first_time_flag(accounts):
    user = accounts.sign_in("lena", "5170")
    assert user["must_change"] and user["role"] == "crew" and "pin_hash" not in user


def test_wrong_pins_lock_and_locks_grow(accounts):
    for _ in range(4):
        with pytest.raises(AuthError, match="(try|tries) left"):
            accounts.sign_in("lena", "0000")
    with pytest.raises(AuthError, match="Locked for 60 seconds"):
        accounts.sign_in("lena", "0000")
    with pytest.raises(AuthError, match="Try again in"):
        accounts.sign_in("lena", "5170")  # even the right PIN waits
    accounts.clock_value[0] += 61
    for _ in range(4):
        with pytest.raises(AuthError):
            accounts.sign_in("lena", "0000")
    with pytest.raises(AuthError, match="Locked for 120 seconds"):
        accounts.sign_in("lena", "0000")
    accounts.unlock("lena")
    assert accounts.sign_in("lena", "5170")["id"] == "lena"


def test_change_pin_needs_the_old_one(accounts):
    with pytest.raises(AuthError):
        accounts.change_pin("lena", "0000", "3918")
    accounts.change_pin("lena", "5170", "3918")
    assert not accounts.sign_in("lena", "3918")["must_change"]


def test_turned_off_accounts_cannot_sign_in(accounts):
    accounts.update("lena", active=False)
    with pytest.raises(AuthError, match="turned off"):
        accounts.sign_in("lena", "5170")


def test_last_commander_stays(accounts):
    with pytest.raises(AuthError, match="at least one active Commander"):
        accounts.update("ana", role="crew")
    with pytest.raises(AuthError):
        accounts.update("ana", active=False)
    accounts.create("Tomas Okafor", "commander", "6203", iterations=FAST)
    assert accounts.update("ana", role="crew")["role"] == "crew"


def test_ids_skip_titles_and_stay_unique(accounts):
    assert accounts.create("Dr. Kai Sato", "ground", "8402", iterations=FAST)["id"] == "kai"
    assert accounts.create("Lena Park", "crew", "8402", iterations=FAST)["id"] == "lena2"


@pytest.mark.parametrize("args", [("", "crew"), ("A" * 41, "crew"), ("Bo", "pilot")])
def test_bad_member_details_are_refused(accounts, args):
    with pytest.raises(AuthError):
        accounts.create(*args, "8402", iterations=FAST)


def test_names_are_unique_and_tags_never_collide(accounts):
    with pytest.raises(AuthError, match="account already"):
        accounts.create("lena  NOVAK", "crew", "5933", iterations=FAST)
    assert accounts.create("Luis Nunez", "crew", "5933", iterations=FAST)["tag"] == "LN2"
    with pytest.raises(AuthError, match="account already"):
        accounts.update("luis", name="Ana Reyes")
    assert accounts.update("luis", name="Luis Navarro")["tag"] == "LN2"  # renaming keeps it apart from Lena
