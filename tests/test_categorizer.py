import pandas as pd
import pytest

from ml import api, categorizer as C
from ml.schema import CATEGORIES, UNCATEGORIZED
from ml.train_categorizer import load_split


@pytest.mark.parametrize("desc,typ,expected", [
    ("UPI/SWIGGY*BLR/4392", "debit", "Food Delivery"),
    ("UPI/AMAZON PRIME/123", "debit", "Subscriptions"),     # must beat the generic Amazon -> Shopping rule
    ("AMAZON PAY INDIA 998", "debit", "Shopping"),
    ("NEFT-SALARY-TECHNOVA-1", "credit", "Salary"),
    ("UPI/PRIYA NAIR/55/REFUND", "credit", "Other Income"),
    ("NEFT-AMIT VERMA-99", "debit", "Transfers"),
    ("NEFT-RENT-LANDLORD 21", "debit", "Rent"),
])
def test_rules(desc, typ, expected):
    assert C.rule_category(desc, typ) == expected


def test_rule_returns_none_for_unknown_merchant():
    assert C.rule_category("POS SOME RANDOM SHOP 12", "debit") is None


def test_normalize_strips_ids_and_adds_type():
    assert C.normalize("UPI/SWIGGY*BLR/84667", "debit") == "UPI SWIGGY BLR TYPEDEBIT"


def test_no_train_test_leakage():
    train, ev = load_split()
    k = lambda d: set(d[["date", "description", "amount", "type"]].astype(str).agg("|".join, axis=1))
    assert not (k(train) & k(ev))
    assert len(ev) >= 250


def test_hybrid_beats_zero_and_handles_unknown_via_ml():
    train, ev = load_split()
    pipe = C.fit(train)
    cats, conf, src = C.predict(ev, pipe, "hybrid")
    assert set(cats) <= set(CATEGORIES)
    assert (conf >= 0).all() and (conf <= 1).all()
    assert sum(c == t for c, t in zip(cats, ev["category"])) / len(ev) > 0.95
    unknown = pd.DataFrame({"description": ["POS SOME RANDOM SHOP 12"], "type": ["debit"]})
    c, cf, s = C.predict(unknown, pipe, "hybrid")
    assert s[0] == "ml" and cf[0] < 1.0


def test_api_categorize_contract():
    df = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"] * 3),
                       "description": ["UPI/SWIGGY*BLR/1", "NEFT-SALARY-X-1", "UPI/ALREADY/1"],
                       "amount": [100.0, 5000.0, 50.0], "type": ["debit", "credit", "debit"],
                       "category": [UNCATEGORIZED, UNCATEGORIZED, "Health"]})
    out = api.categorize(df)
    assert list(out["category"]) == ["Food Delivery", "Salary", "Health"]
    assert list(out["category_source"]) == ["rule", "rule", "existing"]     # existing categories untouched
    assert {"confidence", "category_source"} <= set(out.columns)
    assert df["category"].iloc[0] == UNCATEGORIZED                          # input not mutated
