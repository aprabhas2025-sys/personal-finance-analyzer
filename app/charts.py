"""Dashboard charts as pure functions of the shared schema (testable without Streamlit). Light theme only."""
import pandas as pd
import plotly.graph_objects as go

TEMPLATE = "plotly_white"
SPEND, INCOME, RATE = "#E4572E", "#2E8B57", "#1F4E9C"


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar month: month, income, spend, net, savings_rate (NaN when income is 0)."""
    cols = ["month", "income", "spend", "net", "savings_rate"]
    if df is None or df.empty:
        return pd.DataFrame(columns=cols)
    m = df.assign(month=df["date"].dt.to_period("M"))
    pivot = m.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0.0)
    out = pd.DataFrame({"income": pivot.get("credit", 0.0), "spend": pivot.get("debit", 0.0)})
    out["net"] = out["income"] - out["spend"]
    out["savings_rate"] = (out["net"] / out["income"]).where(out["income"] > 0)
    out = out.reset_index()
    out["month"] = out["month"].astype(str)
    return out[cols]


def overall_savings_rate(df: pd.DataFrame):
    inc = df.loc[df["type"] == "credit", "amount"].sum()
    spend = df.loc[df["type"] == "debit", "amount"].sum()
    return float((inc - spend) / inc) if inc > 0 else None


def _style(fig, title, height=340):
    fig.update_layout(template=TEMPLATE, title=title, height=height, margin=dict(l=14, r=14, t=50, b=56),
                      font=dict(family="Inter, system-ui, sans-serif", color="#0b1b3a"),
                      legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="left", x=0), paper_bgcolor="white", plot_bgcolor="white")
    return fig


def fig_income_vs_spend(df):
    s = monthly_summary(df)
    if s.empty:
        return None
    fig = go.Figure([go.Bar(x=s["month"], y=s["income"], name="Income", marker_color=INCOME),
                     go.Bar(x=s["month"], y=s["spend"], name="Spend", marker_color=SPEND)])
    fig.update_layout(barmode="group")
    fig.update_yaxes(tickprefix="₹", separatethousands=True)
    return _style(fig, "Income vs spend by month")


def fig_savings_rate(df):
    s = monthly_summary(df)
    s = s[s["savings_rate"].notna()]
    if s.empty:
        return None
    fig = go.Figure(go.Scatter(x=s["month"], y=s["savings_rate"], mode="lines+markers", name="Savings rate",
                               line=dict(color=RATE, width=3)))
    fig.add_hline(y=0, line_dash="dot", line_color="#999")
    fig.update_yaxes(tickformat=".0%")
    return _style(fig, "Savings rate by month (income − spend) / income")


def fig_category_breakdown(df, top=None):
    d = df[df["type"] == "debit"].groupby("category", as_index=False)["amount"].sum().sort_values("amount")
    if d.empty:
        return None
    if top:
        d = d.tail(top)
    fig = go.Figure(go.Bar(x=d["amount"], y=d["category"], orientation="h", marker_color=SPEND,
                           text=[f"₹{v:,.0f}" for v in d["amount"]], textposition="outside", cliponaxis=False))
    fig.update_xaxes(tickprefix="₹", separatethousands=True, range=[0, float(d["amount"].max()) * 1.2])   # room for the outside value label
    return _style(fig, "Spending by category", height=max(300, 28 * len(d) + 120))


def fig_category_trend(df, top=5):
    """Monthly spend for the top-N categories (stacked), so shifts in habits are visible."""
    d = df[df["type"] == "debit"]
    if d.empty:
        return None
    keep = d.groupby("category")["amount"].sum().nlargest(top).index
    m = (d[d["category"].isin(keep)].assign(month=lambda x: x["date"].dt.to_period("M").astype(str))
         .groupby(["month", "category"], as_index=False)["amount"].sum())
    fig = go.Figure([go.Bar(x=g["month"], y=g["amount"], name=c) for c, g in m.groupby("category")])
    fig.update_layout(barmode="stack")
    fig.update_yaxes(tickprefix="₹", separatethousands=True)
    return _style(fig, f"Monthly spend, top {top} categories")


# ---------------- Day 4: anomalies, subscriptions, forecast ----------------
def fig_anomaly_scatter(flagged_df: pd.DataFrame):
    """Debit amounts over time (log scale); anomalies in red. Needs an `is_anomaly` column."""
    d = flagged_df[flagged_df["type"] == "debit"]
    if d.empty:
        return None
    ok, bad = d[d["is_anomaly"] == 0], d[d["is_anomaly"] == 1]
    fig = go.Figure([
        go.Scatter(x=ok["date"], y=ok["amount"], mode="markers", name="Normal", marker=dict(color="#9AA5B1", size=5, opacity=0.6),
                   text=ok["description"], hovertemplate="%{text}<br>₹%{y:,.0f}<extra></extra>"),
        go.Scatter(x=bad["date"], y=bad["amount"], mode="markers", name="Unusual",
                   marker=dict(color=SPEND, size=10, line=dict(color="white", width=1)),
                   text=bad["description"], hovertemplate="%{text}<br>₹%{y:,.0f}<extra></extra>")])
    fig.update_yaxes(type="log", tickprefix="₹", separatethousands=True)
    return _style(fig, "Debit transactions over time (log scale)")


def subscription_summary(rec: pd.DataFrame, as_of) -> pd.DataFrame:
    """Add monthly_cost (avg_amount normalised to 30.44 days) and due_in_days (vs `as_of`, e.g. the statement end)."""
    if rec is None or rec.empty:
        return pd.DataFrame(columns=list(rec.columns if rec is not None else []) + ["monthly_cost", "due_in_days"])
    out = rec.copy()
    out["monthly_cost"] = (out["avg_amount"] * 30.44 / out["frequency_days"]).round(2)
    out["due_in_days"] = (pd.to_datetime(out["next_due"]) - pd.Timestamp(as_of)).dt.days
    return out.sort_values("monthly_cost", ascending=False).reset_index(drop=True)


def fig_subscription_cost(summary: pd.DataFrame):
    if summary is None or summary.empty:
        return None
    s = summary.sort_values("monthly_cost")
    fig = go.Figure(go.Bar(x=s["monthly_cost"], y=s["merchant"], orientation="h", marker_color=RATE,
                           text=[f"₹{v:,.0f}" for v in s["monthly_cost"]], textposition="outside", cliponaxis=False))
    fig.update_xaxes(tickprefix="₹", separatethousands=True)
    return _style(fig, "Recurring payments, monthly cost", height=max(300, 30 * len(s) + 120))


def fig_forecast_total(mat: pd.DataFrame, forecast_total: float, next_month: str):
    """History of total monthly spend (from ml.forecast.monthly_matrix) plus the next-month forecast point."""
    if mat is None or mat.empty:
        return None
    hist = mat.sum(axis=1)
    months = [str(p) for p in hist.index]
    fig = go.Figure([
        go.Scatter(x=months, y=hist.values, mode="lines+markers", name="Actual", line=dict(color=SPEND, width=3)),
        go.Scatter(x=[months[-1], next_month], y=[hist.values[-1], forecast_total], mode="lines+markers", name="Forecast",
                   line=dict(color=RATE, width=3, dash="dash"), marker=dict(size=[0, 12]))])
    fig.update_yaxes(tickprefix="₹", separatethousands=True, rangemode="tozero")
    return _style(fig, "Total monthly spend and next-month forecast")


def fig_forecast_by_category(mat: pd.DataFrame, fc: pd.DataFrame):
    """Last full month vs forecast, per category."""
    if mat is None or mat.empty or fc is None or fc.empty:
        return None
    last = mat.iloc[-1]
    f = fc.set_index("category")["forecast_amount"]
    cats = f.sort_values().index
    fig = go.Figure([go.Bar(y=cats, x=[last.get(c, 0.0) for c in cats], orientation="h", name=f"Last month ({mat.index[-1]})", marker_color="#9AA5B1"),
                     go.Bar(y=cats, x=f[cats].values, orientation="h", name="Forecast", marker_color=RATE)])
    fig.update_layout(barmode="group")
    fig.update_xaxes(tickprefix="₹", separatethousands=True)
    return _style(fig, "Forecast by category", height=max(340, 36 * len(cats) + 120))


# ---------------- Day 5: budgets ----------------
def fig_budget(table: pd.DataFrame, month_label: str = ""):
    """Spent (latest month) vs monthly limit, per category. Needs the table from app.budgets.status_table."""
    if table is None or table.empty:
        return None
    t = table.sort_values("pct_used")
    colors = [SPEND if s in ("over", "will exceed") else "#E0A100" if s == "near limit" else INCOME for s in t["status"]]
    fig = go.Figure([go.Bar(y=t["category"], x=t["limit"], orientation="h", name="Limit", marker_color="#D5DAE0"),
                     go.Bar(y=t["category"], x=t["spent"], orientation="h", name=f"Spent {month_label}".strip(), marker_color=colors)])
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(tickprefix="₹", separatethousands=True)
    return _style(fig, "Budget vs spend", height=max(300, 40 * len(t) + 120))
