import numpy as np
import pandas as pd
import pytest

from ml import api, forecast as F
from ml.generate_data import generate


def _tx(rows):
    return pd.DataFrame(rows, columns=["date", "description", "amount", "type", "category"]).assign(date=lambda d: pd.to_datetime(d["date"]))


def _series_df(vals, cat="Groceries"):
    """One month per value, split over the 1st and 28th so no month looks partial."""
    rows = []
    for i, v in enumerate(vals):
        rows += [(pd.Timestamp(2025, 1, 1) + pd.DateOffset(months=i), f"A{i}", v / 2, "debit", cat),
                 (pd.Timestamp(2025, 1, 28) + pd.DateOffset(months=i), f"B{i}", v / 2, "debit", cat)]
    return _tx(rows)


def test_contract_columns_debit_only_nonnegative():
    df = generate()
    out = api.forecast(df)
    assert list(out.columns) == ["category", "forecast_amount"]
    assert set(out["category"]) == set(df[df.type == "debit"]["category"])
    assert (out["forecast_amount"] >= 0).all()
    assert out["forecast_amount"].is_monotonic_decreasing


def test_forecast_total_is_in_the_right_ballpark():
    df = generate()
    monthly = df[df.type == "debit"].groupby(df.date.dt.to_period("M"))["amount"].sum().mean()
    assert abs(api.forecast(df)["forecast_amount"].sum() - monthly) / monthly < 0.05     # mean_all ~= mean monthly spend


def test_missing_month_is_zero_filled():
    df = _tx([(pd.Timestamp(2025, 1, 1), "a", 100.0, "debit", "Fuel"), (pd.Timestamp(2025, 3, 28), "b", 300.0, "debit", "Fuel")])
    mat = F.monthly_matrix(df)
    assert list(mat["Fuel"]) == [100.0, 0.0, 300.0]


def test_partial_first_and_last_months_are_trimmed():
    rows = [(pd.Timestamp(2025, 1, 25), "a", 50.0, "debit", "Fuel")]                       # statement starts 25 Jan
    rows += [(pd.Timestamp(2025, m, 15), f"m{m}", 500.0, "debit", "Fuel") for m in range(2, 6)]
    rows += [(pd.Timestamp(2025, 6, 5), "z", 40.0, "debit", "Fuel")]                       # ends 5 Jun
    mat = F.monthly_matrix(_tx(rows))
    assert [str(p) for p in mat.index] == ["2025-02", "2025-03", "2025-04", "2025-05"]
    assert len(F.monthly_matrix(_tx(rows), trim_partial=False)) == 6


def test_constant_series_every_method_returns_the_constant():
    y = np.full(10, 1234.0)
    for name, fn in F.METHODS.items():
        assert fn(y) == pytest.approx(1234.0, rel=1e-6), name


def test_smoothing_follows_a_level_shift_but_mean_does_not():
    y = np.array([100.0] * 8 + [300.0] * 4)
    assert F._ses(y) > F._mean_all(y) and F._moving_avg_3(y) == 300.0


def test_short_history_still_forecasts():
    out = api.forecast(_series_df([700.0]))
    assert out.iloc[0]["forecast_amount"] == 700.0 and len(api.forecast(_series_df([700.0]).iloc[0:0])) == 0


def test_backtest_structure_and_baseline_present():
    bt = F.backtest(generate())
    assert set(bt) == set(F.METHODS) and F.BASELINE in bt and F.METHOD in bt
    assert all(v["folds"] == 6 for v in bt.values())                 # 12 months, min_train 6
    assert all(0 <= v["total_mape"] < 1 and 0 <= v["category_wape"] < 1 for v in bt.values())


def test_backtest_needs_enough_history():
    assert F.backtest(_series_df([100, 110, 120, 130, 140, 150])) == {}


def test_backtest_does_not_peek_at_the_test_month():
    """A huge final month must only hurt ITS OWN fold: folds 6-8 (actual 1000, forecast 1000) stay perfect."""
    base = [1000.0] * 9
    a = F.backtest(_series_df(base + [1000.0]))
    b = F.backtest(_series_df(base + [100000.0]))
    assert a["mean_all"]["total_mape"] == 0.0
    assert b["mean_all"]["total_mape"] == pytest.approx((1 - 1000 / 100000) / 4, rel=1e-6)   # only the last of 4 folds has error


def test_shipped_method_regression_guard():
    bt = F.backtest(generate())
    assert bt[F.METHOD]["total_mape"] < 0.25                          # measured ~0.065 mean over seeds; loose floor
