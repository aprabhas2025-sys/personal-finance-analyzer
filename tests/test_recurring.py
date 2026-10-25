import pandas as pd

from ml import api
from ml.generate_data import FIXED_MONTHLY, generate
from ml.recurring import recurring_key


def test_contract_columns():
    out = api.find_recurring(generate())
    assert list(out.columns) == ["merchant", "avg_amount", "frequency_days", "last_seen", "next_due"]


def test_finds_the_nine_fixed_monthly_payments_on_seed42():
    out = api.find_recurring(generate())
    expected = {recurring_key(t.format(n=1000, l=10)) for _, t, _, _ in FIXED_MONTHLY}
    assert set(out["merchant"]) == expected
    assert out["frequency_days"].between(28, 32).all()


def test_next_due_is_last_seen_plus_frequency():
    out = api.find_recurring(generate())
    assert ((out["next_due"] - out["last_seen"]).dt.days == out["frequency_days"]).all()


def test_habitual_merchants_are_not_recurring():
    out = api.find_recurring(generate())
    for habit in ("SWIGGY", "ZOMATO", "UBER", "OLA", "AMAZON PAY", "BIGBASKET"):
        assert not any(m.startswith(habit) for m in out["merchant"]), habit


def test_amazon_prime_kept_apart_from_amazon_shopping():
    assert recurring_key("UPI/AMAZON PRIME/123") != recurring_key("AMAZON PAY INDIA 998")


def test_needs_three_occurrences():
    rows = pd.DataFrame({"date": pd.to_datetime(["2026-01-05", "2026-02-05"]), "description": ["UPI/NETFLIX/1", "UPI/NETFLIX/2"],
                         "amount": [649.0, 649.0], "type": ["debit", "debit"], "category": ["Subscriptions"] * 2})
    assert api.find_recurring(rows).empty


def test_weekly_rhythm_detected_and_double_charge_ignored():
    d = pd.date_range("2026-01-02", periods=8, freq="7D")
    rows = pd.DataFrame({"date": d, "description": [f"UPI/MILKMAN/{i}" for i in range(8)], "amount": 120.0,
                         "type": "debit", "category": "Groceries"})
    rows = pd.concat([rows, rows.iloc[[3]]])                       # an exact duplicate must not distort the gaps
    out = api.find_recurring(rows)
    assert len(out) == 1 and out.iloc[0]["frequency_days"] == 7


def test_credits_ignored_and_empty_ok():
    sal = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=6, freq="MS"), "description": "NEFT-SALARY-X",
                        "amount": 85000.0, "type": "credit", "category": "Salary"})
    assert api.find_recurring(sal).empty
    assert api.find_recurring(sal.iloc[0:0]).empty
