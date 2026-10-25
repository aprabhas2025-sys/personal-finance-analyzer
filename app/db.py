"""SQLite storage. Local file, no server. Every function takes an optional path so tests can use a temp DB."""
import sqlite3
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


def _conn(path=None):
    path = Path(path or DEFAULT_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.execute(SCHEMA)
    return c


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


def clear(path=None):
    with _conn(path) as c:
        c.execute("DELETE FROM transactions")
