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
    fig.update_layout(template=TEMPLATE, title=title, height=height, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=1.12, x=0), paper_bgcolor="white", plot_bgcolor="white")
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
    fig.update_xaxes(tickprefix="₹", separatethousands=True)
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
