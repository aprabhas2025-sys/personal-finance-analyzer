"""Next-month spend forecast per category, plus a rolling-origin backtest to compare methods honestly.

Series = monthly debit total per category (zero-filled). Candidate methods, all per category:
  moving_avg_3   mean of the last 3 months   <- the BASELINE the README compares against
  mean_all       mean of all history
  ses            simple exponential smoothing, alpha picked per series by one-step SSE
  ets_damped     Holt damped-trend ETS (statsmodels; falls back to ses if unavailable or it fails)

Prophet is deliberately not used: it needs a heavy install and far more history than ~12 monthly points.
The shipped method (METHOD) is chosen from the backtest in ml/eval_forecast.py, not by assumption.
"""
import warnings

import numpy as np
import pandas as pd

METHOD = "mean_all"          # set from ml/eval_forecast.py results; see metrics/forecast_report.md
BASELINE = "moving_avg_3"
MIN_TRAIN = 6                # months of history before the first backtest fold
ALPHAS = np.linspace(0.05, 0.95, 19)


# ---------- data ----------
def monthly_matrix(df: pd.DataFrame, trim_partial: bool = True) -> pd.DataFrame:
    """Rows = months (Period[M]), columns = debit categories, values = total spend. Missing months are 0.

    If the statement clearly starts late in its first month (after the 10th) or ends early in its last
    month (on or before the 20th), that month is partial and would look like a fake spending dip, so it is dropped.
    """
    d = df[df["type"] == "debit"]
    if d.empty:
        return pd.DataFrame()
    first_day, last_day = pd.to_datetime(df["date"]).min(), pd.to_datetime(df["date"]).max()
    m = d.assign(month=pd.to_datetime(d["date"]).dt.to_period("M"))
    mat = m.pivot_table(index="month", columns="category", values="amount", aggfunc="sum", fill_value=0.0)
    mat = mat.reindex(pd.period_range(mat.index.min(), mat.index.max(), freq="M"), fill_value=0.0)
    if trim_partial and len(mat) > 2:
        if first_day.day > 10:
            mat = mat.iloc[1:]
        if last_day.day <= 20:
            mat = mat.iloc[:-1]
    return mat


# ---------- methods: each maps a 1-D history array to a next-month number ----------
def _moving_avg_3(y):
    return float(np.mean(y[-3:]))


def _mean_all(y):
    return float(np.mean(y))


def _ses_level(y, a):
    lvl = y[0]
    for v in y[1:]:
        lvl = a * v + (1 - a) * lvl
    return lvl


def _ses(y):
    if len(y) < 3:
        return float(np.mean(y))
    best = min(ALPHAS, key=lambda a: sum((y[t] - _ses_level(y[:t], a)) ** 2 for t in range(1, len(y))))
    return float(_ses_level(y, best))


def _ets_damped(y):
    if len(y) < 6 or np.ptp(y) == 0:
        return _ses(y)
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()
            f = float(np.asarray(fit.forecast(1))[0])
        return f if np.isfinite(f) else _ses(y)
    except Exception:
        return _ses(y)


METHODS = {"moving_avg_3": _moving_avg_3, "mean_all": _mean_all, "ses": _ses, "ets_damped": _ets_damped}


def _predict_row(mat: pd.DataFrame, method: str) -> pd.Series:
    fn = METHODS[method]
    return pd.Series({c: max(fn(mat[c].to_numpy(dtype=float)), 0.0) for c in mat.columns})


# ---------- public API ----------
def forecast_table(df: pd.DataFrame, method: str = None) -> pd.DataFrame:
    """Columns: category, forecast_amount (debit categories only), largest first."""
    mat = monthly_matrix(df)
    if mat.empty:
        return pd.DataFrame(columns=["category", "forecast_amount"])
    method = method or (METHOD if len(mat) >= 3 else "mean_all")
    out = _predict_row(mat, method).round(2).rename("forecast_amount").rename_axis("category").reset_index()
    return out.sort_values("forecast_amount", ascending=False).reset_index(drop=True)


def backtest(df: pd.DataFrame, methods=None, min_train: int = MIN_TRAIN) -> dict:
    """Expanding-window rolling-origin backtest. For each month t >= min_train, forecast it from months < t.

    Returns {method: {"total_mape": ..., "category_wape": ..., "folds": n}} or {} if too little history.
      total_mape     mean |sum(pred) - sum(actual)| / sum(actual) over folds (month-level total spend)
      category_wape  sum |pred - actual| / sum actual over all category-month cells
                     (per-category MAPE is avoided: months with zero spend make it undefined or explode)
    """
    mat = monthly_matrix(df)
    if len(mat) <= min_train:
        return {}
    res = {}
    for name in (methods or METHODS):
        tot_err, abs_err, act_sum, folds = [], 0.0, 0.0, 0
        for t in range(min_train, len(mat)):
            pred = _predict_row(mat.iloc[:t], name)
            act = mat.iloc[t]
            if act.sum() <= 0:
                continue
            tot_err.append(abs(pred.sum() - act.sum()) / act.sum())
            abs_err += float((pred - act).abs().sum())
            act_sum += float(act.sum())
            folds += 1
        if folds:
            res[name] = {"total_mape": float(np.mean(tot_err)), "category_wape": abs_err / act_sum, "folds": folds}
    return res
