import pandas as pd
import pytest

from app import db, review
from ml import api, categorizer as C
from ml.schema import UNCATEGORIZED
from ml.train_categorizer import load_split


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Stored statement with rule rows (Swiggy) and rule-less 'novel merchant' rows the ML path has to guess."""
    monkeypatch.setattr(api, "USER_MODEL_PATH", tmp_path / "user.joblib")
    base = load_split()[0]
    monkeypatch.setattr(review.feedback, "_base_training_data", lambda: base)
    api._pipe = C.fit(base)
    rows = [(f"2026-01-{d:02d}", f"UPI/SWIGGY*BLR/{d}", 200.0 + d, "debit") for d in range(1, 6)]
    rows += [(f"2026-02-{d:02d}", f"POS ZYLKART STORE {d}", 500.0, "debit") for d in range(1, 7)]
    df = pd.DataFrame(rows, columns=["date", "description", "amount", "type"]).assign(date=lambda d: pd.to_datetime(d["date"]), category=UNCATEGORIZED)
    p = tmp_path / "t.db"
    db.replace_all(api.categorize(df), p)
    yield p, db.load(p)
    api.reload_model()


def _ids(stored, text):
    return list(stored.loc[stored["description"].str.contains(text), "id"])


def test_setup_sanity(env):
    _, s = env
    assert set(s.loc[s.description.str.contains("SWIGGY"), "category_source"]) == {"rule"}
    assert set(s.loc[s.description.str.contains("ZYLKART"), "category_source"]) == {"ml"}


def test_correction_propagates_to_same_merchant_and_overrides_rule(env):
    p, s = env
    out = review.apply_corrections(s, {_ids(s, "SWIGGY")[0]: "Dining Out"}, propagate=True, retrain=False, db_path=p)
    assert out["corrected"] == 1 and out["propagated"] == 4
    after = db.load(p)
    sw = after[after.description.str.contains("SWIGGY")]
    assert set(sw["category"]) == {"Dining Out"} and set(sw["category_source"]) == {"user"} and (sw["confidence"] == 1.0).all()
    assert set(after.loc[after.description.str.contains("ZYLKART"), "category_source"]) == {"ml"}   # other merchants untouched


def test_no_propagation_when_switched_off(env):
    p, s = env
    out = review.apply_corrections(s, {_ids(s, "SWIGGY")[0]: "Dining Out"}, propagate=False, retrain=False, db_path=p)
    assert out["propagated"] == 0 and (db.load(p)["category_source"] == "user").sum() == 1


def test_conflicting_corrections_for_one_merchant_do_not_propagate(env):
    p, s = env
    a, b = _ids(s, "SWIGGY")[:2]
    out = review.apply_corrections(s, {a: "Dining Out", b: "Groceries"}, propagate=True, retrain=False, db_path=p)
    assert out["corrected"] == 2 and out["propagated"] == 0


def test_noop_and_invalid_edits_are_ignored(env):
    p, s = env
    i = _ids(s, "SWIGGY")[0]
    same = review.apply_corrections(s, {i: s.set_index("id").loc[i, "category"]}, retrain=False, db_path=p)
    bad = review.apply_corrections(s, {i: "Not A Category", 999999: "Fuel"}, retrain=False, db_path=p)
    assert same["corrected"] == 0 and bad["corrected"] == 0 and (db.load(p)["category_source"] == "user").sum() == 0


def test_full_loop_retrains_and_repredicts_other_ml_rows(env):
    p, s = env
    zyl = _ids(s, "ZYLKART")
    out = review.apply_corrections(s, {zyl[0]: "Education"}, propagate=False, retrain=True, db_path=p)
    assert out["retrained"] and out["repredicted"] >= 5
    after = db.load(p).set_index("id")
    assert after.loc[zyl[0], "category_source"] == "user"
    assert (after.loc[zyl[1:], "category"] == "Education").all()               # model learned the merchant from one correction
    assert (after.loc[zyl[1:], "category_source"] == "ml").all()                # ...and these are still marked as model output
    assert api.USER_MODEL_PATH.exists()
