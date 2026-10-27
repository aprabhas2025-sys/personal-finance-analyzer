"""SQLite storage. Local file, no server. Every function takes an optional path so tests can use a temp DB."""
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "finance.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('debit','credit')),
    category TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    category_source TEXT NOT NULL DEFAULT 'rule'   -- rule | ml | user | existing
)"""

BUDGET_SCHEMA = """
CREATE TABLE IF NOT EXISTS budgets (
    category TEXT PRIMARY KEY,
    monthly_limit REAL NOT NULL CHECK (monthly_limit > 0)
)"""

# Track which DB files have been initialized so we skip CREATE TABLE IF NOT EXISTS on every call.
_initialized: set[str] = set()


def session_path(session_id: str) -> Path:
    """Per-visitor DB file, so two sessions never read or overwrite each other's statement.

    Lives under <DEFAULT_PATH's folder>/sessions/ (or $FINANCE_DB_DIR, e.g. a temp dir on a host). The id is
    reduced to hex characters so it can never escape that folder.
    """
    safe = "".join(ch for ch in str(session_id) if ch in "0123456789abcdef")
    if not safe:
        raise ValueError("session_id must contain hex characters")
    base = Path(os.environ["FINANCE_DB_DIR"]) if os.environ.get("FINANCE_DB_DIR") else DEFAULT_PATH.parent / "sessions"
    return base / f"{safe}.db"


def account_path(user_id: str) -> Path:
    """A signed-in user's private DB file (kept until they clear it or delete the account; never purged like session files)."""
    safe = "".join(ch for ch in str(user_id) if ch in "0123456789abcdef")
    if not safe:
        raise ValueError("user_id must contain hex characters")
    base = Path(os.environ["FINANCE_DB_DIR"]) if os.environ.get("FINANCE_DB_DIR") else DEFAULT_PATH.parent
    return base / "accounts" / f"{safe}.db"


def purge_old(max_age_hours: float = 24, folder=None, now=None) -> int:
    """Delete session DB files not modified for max_age_hours. Returns how many were removed."""
    folder = Path(folder) if folder else session_path("0").parent
    if not folder.exists():
        return 0
    cutoff = (now if now is not None else time.time()) - max_age_hours * 3600
    removed = 0
    for p in folder.glob("*.db"):
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
                removed += 1
        except OSError:
            pass
    return removed


@contextmanager
def _conn(path=None):
    """Commit on success, roll back on error, and ALWAYS close (an open handle blocks deleting the file on Windows)."""
    path = Path(path or DEFAULT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        # Only run schema creation once per DB file per process
        key = str(path)
        if key not in _initialized:
            conn.execute(SCHEMA)
            conn.execute(BUDGET_SCHEMA)
            _initialized.add(key)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def replace_all(df: pd.DataFrame, path=None) -> int:
    """Replace the stored transactions with df (one statement at a time in the MVP)."""
    rows = df.assign(
        date=df["date"].dt.strftime("%Y-%m-%d"),
        confidence=df.get("confidence", 1.0),
        category_source=df.get("category_source", "existing"),
    )[["date", "description", "amount", "type", "category", "confidence", "category_source"]]
    with _conn(path) as c:
        c.execute("DELETE FROM transactions")
        c.executemany(
            "INSERT INTO transactions (date, description, amount, type, category, confidence, category_source) "
            "VALUES (?,?,?,?,?,?,?)", rows.itertuples(index=False, name=None))
    return len(rows)


def load(path=None) -> pd.DataFrame:
    with _conn(path) as c:
        df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date, id", c, parse_dates=["date"])
    return df


def count(path=None) -> int:
    with _conn(path) as c:
        return c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


def update_category(ids, category, path=None) -> int:
    """User correction: sets category, marks source 'user' and confidence 1.0. (Used by Day 4 feedback loop.)"""
    ids = [int(i) for i in ids]
    if not ids:
        return 0
    with _conn(path) as c:
        q = ",".join("?" * len(ids))
        cur = c.execute(f"UPDATE transactions SET category=?, category_source='user', confidence=1.0 WHERE id IN ({q})",
                        [category, *ids])
        return cur.rowcount


def apply_predictions(rows: pd.DataFrame, path=None) -> int:
    """Write fresh model output back (columns: id, category, confidence, category_source) WITHOUT marking it as user-corrected.
    Rows whose source is currently 'user' are never overwritten."""
    if rows is None or rows.empty:
        return 0
    data = [(r.category, float(r.confidence), r.category_source, int(r.id)) for r in rows.itertuples()]
    with _conn(path) as c:
        cur = c.executemany(
            "UPDATE transactions SET category=?, confidence=?, category_source=? WHERE id=? AND category_source != 'user'", data)
        return cur.rowcount


def save_budgets(budgets: dict, path=None) -> int:
    """Replace the saved monthly limits. Entries with a missing, zero or negative limit are dropped."""
    rows = []
    for cat, lim in (budgets or {}).items():
        try:
            lim = float(lim)
        except (TypeError, ValueError):
            continue
        if lim > 0 and lim == lim and lim != float("inf"):
            rows.append((str(cat), lim))
    with _conn(path) as c:
        c.execute("DELETE FROM budgets")
        c.executemany("INSERT INTO budgets (category, monthly_limit) VALUES (?,?)", rows)
    return len(rows)


def load_budgets(path=None) -> dict:
    with _conn(path) as c:
        return dict(c.execute("SELECT category, monthly_limit FROM budgets ORDER BY category").fetchall())


def clear(path=None):
    """Remove everything this session stored (transactions and budgets)."""
    with _conn(path) as c:
        c.execute("DELETE FROM transactions")
        c.execute("DELETE FROM budgets")
