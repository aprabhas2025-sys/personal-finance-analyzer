import numpy as np
import pandas as pd

from app import charts
from ml.generate_data import generate


def _df():
    return pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-10", "2026-02-01", "2026-02-15", "2026-03-05"]),
                         "description": list("abcde"), "amount": [1000.0, 400.0, 1000.0, 1000.0, 200.0],
                         "type": ["credit", "debit", "credit", "debit", "debit"],
                         "category": ["Salary", "Groceries", "Salary", "Rent", "Groceries"]})


def test_monthly_summary_math():
    s = charts.monthly_summary(_df()).set_index("month")
    assert s.loc["2026-01", "income"] == 1000 and s.loc["2026-01", "spend"] == 400
    assert abs(s.loc["2026-01", "savings_rate"] - 0.6) < 1e-9
    assert s.loc["2026-02", "savings_rate"] == 0                      # spent everything
    assert s.loc["2026-03", "income"] == 0 and np.isnan(s.loc["2026-03", "savings_rate"])   # no income: undefined, not inf


def test_overall_savings_rate():
    assert abs(charts.overall_savings_rate(_df()) - (2000 - 1600) / 2000) < 1e-9
    assert charts.overall_savings_rate(_df()[_df().type == "debit"]) is None


def test_empty_inputs_return_none_not_crash():
    e = _df().iloc[0:0]
    assert charts.monthly_summary(e).empty
    for fn in (charts.fig_income_vs_spend, charts.fig_savings_rate, charts.fig_category_breakdown, charts.fig_category_trend):
        assert fn(e) is None


def test_figures_build_on_real_shaped_data_and_are_light():
    df = generate()
    for fn in (charts.fig_income_vs_spend, charts.fig_savings_rate, charts.fig_category_breakdown, charts.fig_category_trend):
        fig = fn(df)
        assert fig is not None and len(fig.data) >= 1
        assert fig.layout.paper_bgcolor == "white" and fig.layout.plot_bgcolor == "white"


def test_synthetic_savings_rate_is_plausible():
    assert 0.05 < charts.overall_savings_rate(generate()) < 0.40      # handoff says ~18%; loose band, not an exact claim
