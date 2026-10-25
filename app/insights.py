"""Day 4 Streamlit pages: Anomalies, Subscriptions, Forecast, and the category-correction panel."""
import pandas as pd
import streamlit as st

from app import charts, review
from ml import api, forecast as F
from ml.schema import CATEGORIES

_RS = st.column_config.NumberColumn(format="₹%.2f")


@st.cache_data(show_spinner=False)
def _backtest(df: pd.DataFrame):
    return F.backtest(df)


def render_anomalies(f: pd.DataFrame, full: pd.DataFrame):
    an = api.find_anomalies(full.drop(columns=["id"], errors="ignore")).assign(id=full["id"].to_numpy())
    an = an[an["id"].isin(f["id"])]
    flagged = an[an["is_anomaly"] == 1]
    c1, c2 = st.columns(2)
    c1.metric("Unusual transactions", len(flagged))
    c2.metric("Total amount flagged", f"₹{flagged['amount'].sum():,.0f}")
    st.caption("Flags duplicate charges and amounts far above what is normal for their category. "
               "It is a prompt to check, not proof of a problem, and it only looks for those two patterns.")
    fig = charts.fig_anomaly_scatter(an)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    if flagged.empty:
        st.success("Nothing unusual in the current filter.")
        return
    v = flagged.assign(date=flagged["date"].dt.date)[["date", "description", "amount", "category", "anomaly_reason"]]
    st.dataframe(v, width="stretch", hide_index=True, column_config={"amount": _RS})


def render_subscriptions(full: pd.DataFrame):
    rec = charts.subscription_summary(api.find_recurring(full), full["date"].max())
    if rec.empty:
        st.info("No recurring payments found. At least 3 regular payments to the same merchant are needed.")
        return
    soon = rec[(rec["due_in_days"] >= 0) & (rec["due_in_days"] <= 30)]
    c1, c2, c3 = st.columns(3)
    c1.metric("Recurring payments", len(rec))
    c2.metric("Monthly commitment", f"₹{rec['monthly_cost'].sum():,.0f}")
    c3.metric("Due within 30 days of statement end", len(soon), f"₹{soon['avg_amount'].sum():,.0f}", delta_color="off")
    fig = charts.fig_subscription_cost(rec)
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    v = rec.assign(last_seen=rec["last_seen"].dt.date, next_due=rec["next_due"].dt.date)[
        ["merchant", "avg_amount", "monthly_cost", "frequency_days", "last_seen", "next_due", "due_in_days"]]
    st.dataframe(v, width="stretch", hide_index=True, column_config={"avg_amount": _RS, "monthly_cost": _RS})
    st.caption("Dates are relative to the end of your statement, not today. Variable bills (electricity) show their average.")


def render_forecast(full: pd.DataFrame):
    mat = F.monthly_matrix(full)
    fc = api.forecast(full)
    if mat.empty or fc.empty:
        st.info("Not enough spending history to forecast.")
        return
    nxt = str(mat.index[-1] + 1)
    total = float(fc["forecast_amount"].sum())
    last3 = float(mat.iloc[-3:].sum(axis=1).mean())
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Forecast spend, {nxt}", f"₹{total:,.0f}", f"{(total - last3) / last3:+.0%} vs last 3 months" if last3 else None, delta_color="off")
    c2.metric("Months of history", len(mat))
    c3.metric("Method", F.METHOD.replace("_", " "))
    if len(mat) < 6:
        st.warning("Under 6 months of history: treat this forecast as a rough guide.")
    a, b = st.columns(2)
    with a:
        st.plotly_chart(charts.fig_forecast_total(mat, total, nxt), width="stretch")
    with b:
        st.plotly_chart(charts.fig_forecast_by_category(mat, fc), width="stretch")

    st.subheader("How accurate is this on your data?")
    bt = _backtest(full)
    if not bt:
        st.info(f"A backtest needs more than {F.MIN_TRAIN + 1} months of history (you have {len(mat)}).")
        return
    rows = [{"method": n + (" (baseline)" if n == F.BASELINE else " (shipped)" if n == F.METHOD else ""),
             "total-spend MAPE": f"{r['total_mape']:.1%}", "category WAPE": f"{r['category_wape']:.1%}", "months tested": r["folds"]}
            for n, r in bt.items()]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption("Rolling backtest: each tested month is forecast using only the months before it. "
               "With about a year of data these numbers are noisy; a method winning here is weak evidence.")


def render_review(f: pd.DataFrame, full: pd.DataFrame):
    """Editable category column for the least-confident rows. Applying corrections retrains the model."""
    with st.expander("Review & correct categories", expanded=False):
        st.caption("Change a category and apply. The correction can also be applied to every transaction from the same merchant, "
                   "and the model is retrained so similar transactions are categorized better. Least confident rows first.")
        n = st.session_state.setdefault("review_n", 0)
        view = f.sort_values("confidence").head(150)
        edit_src = view.assign(date=view["date"].dt.date)[["id", "date", "description", "amount", "type", "category", "confidence", "category_source"]]
        edited = st.data_editor(
            edit_src, key=f"review_editor_{n}", hide_index=True, width="stretch", height=320,
            disabled=[c for c in edit_src.columns if c != "category"],
            column_config={"category": st.column_config.SelectboxColumn(options=CATEGORIES, required=True),
                           "amount": _RS, "confidence": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
        propagate = st.checkbox("Apply to all transactions from the same merchant", value=True)
        changed = edited.loc[edited["category"].to_numpy() != edit_src["category"].to_numpy()]
        if st.button(f"Apply {len(changed)} correction(s)", disabled=changed.empty, type="primary"):
            with st.spinner("Saving and retraining…"):
                s = review.apply_corrections(full, dict(zip(changed["id"], changed["category"])), propagate=propagate)
            st.session_state["review_n"] = n + 1
            st.session_state["review_msg"] = (f"Corrected {s['corrected']} + {s['propagated']} same-merchant transactions. "
                                              f"Model retrained; {s['changed_by_model']} other predictions changed.")
            st.rerun()
        if st.session_state.get("review_msg"):
            st.success(st.session_state.pop("review_msg"))
