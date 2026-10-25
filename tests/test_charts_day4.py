import pandas as pd

from app import charts
from ml import api, forecast as F
from ml.generate_data import generate


def test_subscription_summary_math_and_order():
    rec = pd.DataFrame({"merchant": ["NETFLIX COM", "MILK"], "avg_amount": [649.0, 100.0], "frequency_days": [30, 7],
                        "last_seen": pd.to_datetime(["2026-10-09", "2026-10-28"]), "next_due": pd.to_datetime(["2026-11-08", "2026-11-04"])})
    s = charts.subscription_summary(rec, pd.Timestamp("2026-10-31"))
    assert list(s["merchant"]) == ["NETFLIX COM", "MILK"] or s["monthly_cost"].is_monotonic_decreasing
    nf = s.set_index("merchant")
    assert abs(nf.loc["NETFLIX COM", "monthly_cost"] - 649 * 30.44 / 30) < 0.01
    assert abs(nf.loc["MILK", "monthly_cost"] - 100 * 30.44 / 7) < 0.01 and nf.loc["MILK", "due_in_days"] == 4


def test_empty_inputs_give_none():
    e = pd.DataFrame(columns=["merchant", "avg_amount", "frequency_days", "last_seen", "next_due"])
    assert charts.subscription_summary(e, pd.Timestamp("2026-01-01")).empty
    assert charts.fig_subscription_cost(e) is None
    assert charts.fig_forecast_total(pd.DataFrame(), 0.0, "2026-11") is None
    assert charts.fig_forecast_by_category(pd.DataFrame(), pd.DataFrame()) is None


def test_figures_build_and_are_light():
    df = generate()
    mat, fc = F.monthly_matrix(df), api.forecast(df)
    figs = [charts.fig_anomaly_scatter(api.find_anomalies(df)),
            charts.fig_subscription_cost(charts.subscription_summary(api.find_recurring(df), df.date.max())),
            charts.fig_forecast_total(mat, float(fc.forecast_amount.sum()), str(mat.index[-1] + 1)),
            charts.fig_forecast_by_category(mat, fc)]
    for fig in figs:
        assert fig is not None and len(fig.data) >= 1 and fig.layout.paper_bgcolor == "white"
    assert len(figs[0].data[1].x) == 12                                        # 12 flagged points highlighted
    assert list(figs[2].data[1].x)[-1] == str(mat.index[-1] + 1)
