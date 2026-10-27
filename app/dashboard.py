"""Dashboard tab: KPIs + charts, plus a compact view of Person A's anomalies and recurring payments."""
import pandas as pd
import streamlit as st

from app import charts
from ml import api


def prepare(f: pd.DataFrame, full: pd.DataFrame):
    """Compute the compact KPI summary once for both the overview and chart tab."""
    sr = charts.overall_savings_rate(f)
    flagged = api.find_anomalies(full.drop(columns=["id"], errors="ignore"))
    flagged = flagged.assign(id=full["id"].to_numpy())
    flagged = flagged[(flagged["is_anomaly"] == 1) & flagged["id"].isin(f["id"])]
    rec = api.find_recurring(full)
    monthly = charts.monthly_summary(f)
    avg_spend = float(monthly["spend"].mean()) if not monthly.empty else 0.0
    return {"savings_rate": sr, "avg_spend": avg_spend, "flagged": flagged, "recurring": rec}


def render(f: pd.DataFrame, full: pd.DataFrame, summary=None):
    """Render charts and detail tables; KPI cards are shown above the navigation."""
    if f.empty:
        st.info("No transactions match the current filters.")
        return
    summary = summary or prepare(f, full)
    flagged, rec = summary["flagged"], summary["recurring"]
    a, b = st.columns(2)
    with a:
        st.plotly_chart(charts.fig_income_vs_spend(f), width="stretch")
    with b:
        fig = charts.fig_savings_rate(f)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
    c, d = st.columns(2)
    with c:
        fig = charts.fig_category_breakdown(f)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
    with d:
        fig = charts.fig_category_trend(f)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")

    if len(flagged):
        st.subheader("Unusual transactions")
        v = flagged.assign(date=flagged["date"].dt.date)[["date", "description", "amount", "category", "anomaly_reason"]]
        st.dataframe(v, width="stretch", hide_index=True,
                     column_config={"amount": st.column_config.NumberColumn(format="₹%.2f")})
    if len(rec):
        st.subheader("Recurring payments")
        v = rec.assign(last_seen=rec["last_seen"].dt.date, next_due=rec["next_due"].dt.date)
        st.dataframe(v, width="stretch", hide_index=True,
                     column_config={"avg_amount": st.column_config.NumberColumn(format="₹%.2f")})
