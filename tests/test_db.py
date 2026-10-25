import pandas as pd
from app import db


def _df():
    return pd.DataFrame({"date": pd.to_datetime(["2026-01-02", "2026-01-01"]),
                         "description": ["B", "A"], "amount": [10.0, 20.0], "type": ["debit", "credit"],
                         "category": ["Shopping", "Salary"], "confidence": [0.4, 1.0], "category_source": ["ml", "rule"]})


def test_roundtrip_sorted_by_date(tmp_path):
    p = tmp_path / "t.db"
    assert db.replace_all(_df(), p) == 2
    out = db.load(p)
    assert list(out["description"]) == ["A", "B"]
    assert out["date"].dtype.kind == "M" and "id" in out.columns


def test_replace_overwrites(tmp_path):
    p = tmp_path / "t.db"
    db.replace_all(_df(), p)
    db.replace_all(_df().head(1), p)
    assert db.count(p) == 1


def test_update_category_marks_user(tmp_path):
    p = tmp_path / "t.db"
    db.replace_all(_df(), p)
    row = db.load(p).query("description == 'B'").iloc[0]
    assert db.update_category([row["id"]], "Health", p) == 1
    new = db.load(p).query("description == 'B'").iloc[0]
    assert (new["category"], new["category_source"], new["confidence"]) == ("Health", "user", 1.0)


def test_clear_and_empty_load(tmp_path):
    p = tmp_path / "t.db"
    assert db.load(p).empty
    db.replace_all(_df(), p)
    db.clear(p)
    assert db.count(p) == 0
