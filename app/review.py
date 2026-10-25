"""Apply the user's category corrections: write them, optionally spread them to the same merchant, retrain, re-predict.

Kept free of Streamlit so it can be tested directly.
"""
import pandas as pd

from app import db
from ml import api, feedback
from ml.recurring import recurring_key
from ml.schema import CATEGORIES, UNCATEGORIZED


def _merchant(df):
    return df["description"].map(recurring_key) + "|" + df["type"].astype(str)


def apply_corrections(stored: pd.DataFrame, edits: dict, propagate: bool = True, retrain: bool = True, db_path=None) -> dict:
    """stored = db.load() output; edits = {transaction id: new category}.

    1. each edited row gets its new category (source 'user')
    2. propagate=True: other rows of the same merchant+type that were not user-set get that category too,
       unless the user gave one merchant two different categories in this batch (then it is skipped)
    3. retrain=True: retrain the ML model on all user-set rows and re-predict the remaining ML-sourced rows
    """
    cur = stored.set_index("id")["category"]
    edits = {int(i): c for i, c in edits.items() if int(i) in cur.index and c in CATEGORIES and c != cur[int(i)]}
    summary = {"corrected": len(edits), "propagated": 0, "retrained": False, "repredicted": 0, "changed_by_model": 0}
    if not edits:
        return summary

    assign = dict(edits)
    if propagate:
        keys = _merchant(stored)
        key_of = dict(zip(stored["id"], keys))
        chosen = {}
        for i, c in edits.items():
            chosen.setdefault(key_of[i], set()).add(c)
        for k, cats in chosen.items():
            if len(cats) != 1:
                continue
            cat = next(iter(cats))
            same = stored[(keys == k) & (stored["category_source"] != "user") & (stored["category"] != cat)]
            for i in same["id"]:
                assign.setdefault(int(i), cat)
        summary["propagated"] = len(assign) - len(edits)

    by_cat = {}
    for i, c in assign.items():
        by_cat.setdefault(c, []).append(i)
    for c, ids in by_cat.items():
        db.update_category(ids, c, db_path)

    if retrain:
        after = db.load(db_path)
        feedback.retrain_with_corrections(after.loc[after["category_source"] == "user", ["description", "type", "category"]])
        summary["retrained"] = True
        ml_rows = after[after["category_source"] == "ml"]
        if len(ml_rows):
            fresh = api.categorize(ml_rows.drop(columns=["confidence", "category_source"]).assign(category=UNCATEGORIZED))
            fresh = fresh.assign(id=ml_rows["id"].to_numpy())
            changed = fresh[fresh["category"].to_numpy() != ml_rows["category"].to_numpy()]
            db.apply_predictions(fresh[["id", "category", "confidence", "category_source"]], db_path)
            summary["repredicted"], summary["changed_by_model"] = len(fresh), len(changed)
    return summary
