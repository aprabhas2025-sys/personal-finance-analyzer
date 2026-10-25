import pandas as pd
import pytest

from ml import api, categorizer as C, feedback
from ml.train_categorizer import load_split


@pytest.fixture(scope="module")
def base():
    return load_split()[0]


def _novel(n=6, name="ZYLKART"):
    return pd.DataFrame({"description": [f"POS {name} STORE {i}" for i in range(n)], "type": "debit"})


def test_clean_corrections_drops_bad_categories_and_dedupes_same_text():
    c = pd.DataFrame({"description": ["UPI/FOO/111", "UPI/FOO/222", "UPI/BAR/1", "UPI/BAZ/1"], "type": "debit",
                      "category": ["Groceries", "Groceries", "NotACategory", "Fuel"]})
    out = feedback.clean_corrections(c)
    assert len(out) == 2 and set(out["category"]) == {"Groceries", "Fuel"}      # FOO/111 and FOO/222 normalize alike


def test_corrections_teach_the_model_a_new_merchant(base):
    before = C.fit(base)
    corr = _novel(1).assign(category="Education")
    after = feedback.train_with_corrections(base, corr)
    test = _novel(6, "ZYLKART").iloc[1:]
    assert (pd.Series(C.predict(test, after, "ml")[0]) == "Education").all()
    assert not (pd.Series(C.predict(test, before, "ml")[0]) == "Education").all()


def test_nothing_to_train_on_raises():
    with pytest.raises(ValueError):
        feedback.train_with_corrections(None, pd.DataFrame(columns=feedback.NEEDED))


def test_retrain_saves_user_model_and_api_prefers_it(base, tmp_path, monkeypatch):
    monkeypatch.setattr(api, "USER_MODEL_PATH", tmp_path / "user.joblib")
    corr = _novel(1, "QWERTYPAY").assign(category="Health")
    feedback.retrain_with_corrections(corr, base=base)
    assert (tmp_path / "user.joblib").exists() and api._pipe is None           # reset so the next call reloads
    df = _novel(3, "QWERTYPAY").assign(date=pd.Timestamp("2026-01-01"), amount=100.0, category="Uncategorized")
    out = api.categorize(df)
    assert list(out["category"]) == ["Health"] * 3 and list(out["category_source"]) == ["ml"] * 3
    api.reload_model()
