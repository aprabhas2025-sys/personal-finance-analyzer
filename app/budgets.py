"""Monthly category budgets: compare limits with the latest month's spend and with the next-month forecast. Pure pandas, no Streamlit."""
import math

import pandas as pd

NEAR = 0.8          # used >= 80% of the limit counts as "near limit"
COLUMNS = ["category", "limit", "spent", "pct_used", "forecast", "status"]


def latest_month(df: pd.DataFrame):
    """(Period, is_partial). A month is partial when the statement ends before its last calendar day."""
    last = pd.to_datetime(df["date"]).max()
    p = last.to_period("M")
    return p, last.normalize() < p.end_time.normalize()


def status_table(df: pd.DataFrame, budgets: dict, forecast: pd.DataFrame | None = None):
    """Returns (table, meta). table columns: category, limit, spent (latest month), pct_used, forecast (next month), status.

    status: 'over' (spent > limit), 'will exceed' (forecast > limit), 'near limit' (>= 80% used), 'ok'.
    meta: {"month": "2026-03", "partial": bool}. Empty table when there are no budgets or no data.
    """
    budgets = {c: float(v) for c, v in (budgets or {}).items() if v and float(v) > 0}
    if df is None or df.empty or not budgets:
        return pd.DataFrame(columns=COLUMNS), {"month": None, "partial": False}
    d = df.assign(date=pd.to_datetime(df["date"]))
    month, partial = latest_month(d)
    spent = d[(d["type"] == "debit") & (d["date"].dt.to_period("M") == month)].groupby("category")["amount"].sum()
    fc = forecast.set_index("category")["forecast_amount"] if forecast is not None and not forecast.empty else pd.Series(dtype=float)
    rows = []
    for cat, lim in budgets.items():
        s, f = float(spent.get(cat, 0.0)), (float(fc[cat]) if cat in fc.index else math.nan)
        pct = s / lim
        st = "over" if s > lim else "will exceed" if (not math.isnan(f) and f > lim) else "near limit" if pct >= NEAR else "ok"
        rows.append((cat, lim, round(s, 2), round(pct, 4), None if math.isnan(f) else round(f, 2), st))
    out = pd.DataFrame(rows, columns=COLUMNS).sort_values("pct_used", ascending=False).reset_index(drop=True)
    return out, {"month": str(month), "partial": bool(partial)}


def suggest(df: pd.DataFrame, margin: float = 1.1, round_to: int = 100) -> dict:
    """Suggested limits: average monthly spend per category over complete months, +10%, rounded up to the nearest 100."""
    d = df[df["type"] == "debit"]
    if d.empty:
        return {}
    d = d.assign(month=pd.to_datetime(d["date"]).dt.to_period("M"))
    month, partial = latest_month(df)
    first = pd.to_datetime(df["date"]).min()
    months = pd.period_range(first.to_period("M"), month, freq="M")
    if partial and len(months) > 1:
        months = months[:-1]
    if first.day > 10 and len(months) > 1:
        months = months[1:]
    d = d[d["month"].isin(months)]
    avg = d.pivot_table(index="month", columns="category", values="amount", aggfunc="sum", fill_value=0.0).reindex(months, fill_value=0.0).mean()
    return {c: float(math.ceil(v * margin / round_to) * round_to) for c, v in avg.items() if v > 0}
