import pandas as pd

from app import db


def _df():
    return pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-02"]), "description": ["A", "B"], "amount": [1.0, 2.0],
                         "type": ["debit", "debit"], "category": ["Fuel", "Fuel"], "confidence": [0.3, 0.3], "category_source": ["ml", "ml"]})


def test_apply_predictions_updates_but_never_overwrites_user_rows(tmp_path):
    p = tmp_path / "t.db"
    db.replace_all(_df(), p)
    ids = list(db.load(p)["id"])
    db.update_category([ids[1]], "Health", p)                                    # user fixes row 2
    rows = pd.DataFrame({"id": ids, "category": ["Groceries", "Groceries"], "confidence": [0.9, 0.9], "category_source": ["ml", "ml"]})
    db.apply_predictions(rows, p)
    out = db.load(p).set_index("id")
    assert out.loc[ids[0], "category"] == "Groceries" and out.loc[ids[0], "confidence"] == 0.9
    assert out.loc[ids[1], "category"] == "Health" and out.loc[ids[1], "category_source"] == "user"


def test_apply_predictions_empty_is_noop(tmp_path):
    p = tmp_path / "t.db"
    db.replace_all(_df(), p)
    assert db.apply_predictions(pd.DataFrame(columns=["id", "category", "confidence", "category_source"]), p) == 0
