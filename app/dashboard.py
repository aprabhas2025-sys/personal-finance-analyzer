"""Dashboard tab: KPIs + charts, plus a compact view of Person A's anomalies and recurring payments."""
import pandas as pd
import streamlit as st

from app import charts


def render(f: pd.DataFrame, full: pd.DataFrame, anomaly_result: pd.DataFrame = None, recurring_result: pd.DataFrame = None):
    """f = rows after sidebar filters (charts use this); full = all stored rows (anomaly/recurring context).

    anomaly_result and recurring_result are pre-computed in app.py to avoid redundant computation.
    """
    if f.empty:
        st.info("No transactions match the current filters.")
        return

    sr = charts.overall_savings_rate(f)

    # Use pre-computed results instead of re-running expensive ML
    if anomaly_result is not None:
        flagged = anomaly_result.assign(id=full["id"].to_numpy())
        flagged = flagged[(flagged["is_anomaly"] == 1) & flagged["id"].isin(f["id"])]
    else:
        from ml import api
        flagged_all = api.find_anomalies(full.drop(columns=["id"], errors="ignore"))
        flagged = flagged_all.assign(id=full["id"].to_numpy())
        flagged = flagged[(flagged["is_anomaly"] == 1) & flagged["id"].isin(f["id"])]

    if recurring_result is not None:
        rec = recurring_result
    else:
        from ml import api
        rec = api.find_recurring(full)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Savings rate", f"{sr:.0%}" if sr is not None else "n/a", help="(income − spend) / income, filtered range")
    k2.metric("Avg monthly spend", f"₹{charts.monthly_summary(f)['spend'].mean():,.0f}")
    k3.metric("Unusual transactions", len(flagged), help="Duplicates and amounts far above the category norm")
    k4.metric("Recurring payments", len(rec), f"₹{rec['avg_amount'].sum():,.0f}/cycle" if len(rec) else None, delta_color="off")

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
