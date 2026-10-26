"""Accounts: email + password, stored in a small SQLite file. No Streamlit, no network.

- Passwords are never stored: only a salted scrypt hash (stdlib hashlib.scrypt), compared in constant time.
- Wrong email and wrong password give the SAME message, and unknown emails cost the same time as known ones.
- 5 wrong passwords lock the account for 5 minutes (slows guessing).
- Each user gets a random hex id; their transactions live in their own DB file (app.db.account_path).
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from app import db

MIN_PASSWORD, MAX_PASSWORD, MAX_EMAIL = 8, 128, 254
MAX_FAILS, LOCK_SECONDS = 5, 300
_N, _R, _P = 2 ** 14, 8, 1
BAD_LOGIN = "Incorrect email or password."
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    pw_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until REAL NOT NULL DEFAULT 0
)"""


def users_db_path() -> Path:
    base = Path(os.environ["FINANCE_DB_DIR"]) if os.environ.get("FINANCE_DB_DIR") else db.DEFAULT_PATH.parent
    return base / "users.db"


@contextmanager
def _conn():
    p = users_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(p)
    try:
        c.execute(SCHEMA)
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


# ---------- hashing ----------
def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, h = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=len(h) // 2)
        return hmac.compare_digest(calc.hex(), h)
    except (ValueError, TypeError):
        return False


_DUMMY = hash_password("dummy-password-for-timing")      # unknown emails still pay for one hash


# ---------- validation ----------
def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_email(email: str) -> str | None:
    e = normalize_email(email)
    if not e or len(e) > MAX_EMAIL or not _EMAIL.match(e):
        return "Enter a valid email address."
    return None


def validate_password(password: str) -> str | None:
    if len(password or "") < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return f"Use at most {MAX_PASSWORD} characters."
    if password.lower() in {"password", "12345678", "123456789", "qwertyui", "password1", "iloveyou"}:
        return "That password is too common. Choose another."
    return None


# ---------- accounts ----------
def create_user(email: str, password: str, confirm: str | None = None):
    """Returns (user_dict, None) or (None, error message)."""
    err = validate_email(email) or validate_password(password)
    if err:
        return None, err
    if confirm is not None and confirm != password:
        return None, "The two passwords do not match."
    email, uid = normalize_email(email), secrets.token_hex(16)
    try:
        with _conn() as c:
            c.execute("INSERT INTO users (id, email, pw_hash, created_at) VALUES (?,?,?,?)", (uid, email, hash_password(password), time.time()))
    except sqlite3.IntegrityError:
        return None, "An account with this email already exists. Try signing in."
    return {"id": uid, "email": email}, None


def authenticate(email: str, password: str, now: float | None = None):
    """Returns (user_dict, None) or (None, error message)."""
    now = time.time() if now is None else now
    email = normalize_email(email)
    if not email or not password or len(password) > MAX_PASSWORD or len(email) > MAX_EMAIL:
        return None, BAD_LOGIN
    with _conn() as c:
        row = c.execute("SELECT id, pw_hash, failed_attempts, locked_until FROM users WHERE email=?", (email,)).fetchone()
        if row is None:
            verify_password(password, _DUMMY)
            return None, BAD_LOGIN
        uid, stored, fails, locked_until = row
        if locked_until > now:
            return None, f"Too many attempts. Try again in {int((locked_until - now) // 60) + 1} minute(s)."
        if verify_password(password, stored):
            c.execute("UPDATE users SET failed_attempts=0, locked_until=0 WHERE id=?", (uid,))
            return {"id": uid, "email": email}, None
        fails += 1
        if fails >= MAX_FAILS:
            c.execute("UPDATE users SET failed_attempts=0, locked_until=? WHERE id=?", (now + LOCK_SECONDS, uid))
        else:
            c.execute("UPDATE users SET failed_attempts=? WHERE id=?", (fails, uid))
        return None, BAD_LOGIN


def delete_user(uid: str) -> bool:
    """Remove the account and the user's stored data file."""
    with _conn() as c:
        n = c.execute("DELETE FROM users WHERE id=?", (uid,)).rowcount
    try:
        db.account_path(uid).unlink(missing_ok=True)
    except (OSError, ValueError):
        pass
    return n > 0
