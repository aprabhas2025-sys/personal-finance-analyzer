"""Streamlit app. Run from the project root:  streamlit run app/app.py"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from app import auth, budgets_ui, chat_ui, config, dashboard, db, insights, landing
from app.cleaning import CleaningError, clean_transactions
from ml import api
from ml.schema import CATEGORIES

st.set_page_config(page_title="Finora | Personal Finance", page_icon="📈", layout="wide")
USER = landing.require_login()          # signed out: landing / sign-in / sign-up page, then st.stop(). Signed in: carry on to the app.
st.title("Finora")
HOSTED = config.is_hosted()
st.caption(config.HOSTED_CAPTION if HOSTED else config.LOCAL_CAPTION)
if st.session_state.pop("just_signed_in", False):
    st.toast(f"Signed in as {USER['email']}")

SAMPLE = ROOT / "data" / "synthetic_bank_export.csv"

# One private DB file per account, so users can never see or overwrite each other's data.
DB_PATH = db.account_path(USER["id"])


def ingest(raw: pd.DataFrame):
    df, report = clean_transactions(raw)
    df = api.categorize(df)                    # Person A's model
    db.replace_all(df, DB_PATH)
    st.session_state["report"] = report
    # Invalidate cached computations when new data is ingested
    _cached_anomalies.clear()
    _cached_recurring.clear()
    _cached_forecast.clear()


# ------------ Cached expensive ML computations (computed once per data snapshot) ------------
@st.cache_data(show_spinner=False, max_entries=4, ttl=1800)
def _cached_anomalies(_df_hash: str, df: pd.DataFrame) -> pd.DataFrame:
    return api.find_anomalies(df.drop(columns=["id"], errors="ignore"))

@st.cache_data(show_spinner=False, max_entries=4, ttl=1800)
def _cached_recurring(_df_hash: str, df: pd.DataFrame) -> pd.DataFrame:
    return api.find_recurring(df)

@st.cache_data(show_spinner=False, max_entries=4, ttl=1800)
def _cached_forecast(_df_hash: str, df: pd.DataFrame) -> pd.DataFrame:
    return api.forecast(df.drop(columns=["id"], errors="ignore"))


def _df_signature(df: pd.DataFrame) -> str:
    """Cheap hash of the dataframe shape + a sample of values to use as cache key."""
    n = len(df)
    if n == 0:
        return "empty"
    sample_vals = f"{n}_{df['amount'].sum():.2f}_{df['date'].iloc[0]}_{df['date'].iloc[-1]}"
    return hashlib.md5(sample_vals.encode()).hexdigest()


# ---------------- sidebar: load data ----------------
with st.sidebar:
    st.caption(f"Signed in as **{USER['email']}**")
    if st.button("Sign out"):
        st.session_state.clear()               # also drops chat history and any loaded state, so the next user starts clean
        st.rerun()
    with st.expander("Account"):
        sure = st.checkbox("Permanently delete my account and data")
        if st.button("Delete my account", disabled=not sure):
            auth.delete_user(USER["id"])
            st.session_state.clear()
            st.rerun()
    st.header("1. Load data")
    up = st.file_uploader("Bank statement (CSV)", type=["csv"])
    use_sample = st.button("Use sample data", disabled=not SAMPLE.exists())
    if st.button("Clear stored data"):
        db.clear(DB_PATH)
        st.session_state.pop("loaded_sig", None)
        st.session_state.pop("report", None)

source = None
if up is not None:
    source = ("upload", up.getvalue())
elif use_sample:
    source = ("sample", SAMPLE.read_bytes())

if source is not None:
    sig = hashlib.md5(source[1]).hexdigest()
    if st.session_state.get("loaded_sig") != sig:           # don't reprocess on every rerun
        try:
            import io
            ingest(pd.read_csv(io.BytesIO(source[1]), dtype=str))
            st.session_state["loaded_sig"] = sig
        except CleaningError as e:
            st.error(str(e))
            st.stop()

df = db.load(DB_PATH)
if df.empty:
    st.info("Upload a CSV or click **Use sample data** in the sidebar to begin.")
    st.stop()

# Pre-compute expensive results ONCE and share across all tabs
_sig = _df_signature(df)
anomaly_result = _cached_anomalies(_sig, df)
recurring_result = _cached_recurring(_sig, df)
forecast_result = _cached_forecast(_sig, df)

# ---------------- sidebar: filters ----------------
with st.sidebar:
    st.header("2. Filters")
    dmin, dmax = df["date"].min().date(), df["date"].max().date()
    rng = st.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
    types = st.multiselect("Type", ["debit", "credit"], default=["debit", "credit"])
    cats = st.multiselect("Category", sorted(df["category"].unique()))
    text = st.text_input("Search description")
    review_only = st.checkbox(f"Needs review only (confidence < {api.REVIEW_THRESHOLD:.0%})")

f = df.copy()
if isinstance(rng, tuple) and len(rng) == 2:
    f = f[(f["date"].dt.date >= rng[0]) & (f["date"].dt.date <= rng[1])]
f = f[f["type"].isin(types)]
if cats:
    f = f[f["category"].isin(cats)]
if text:
    f = f[f["description"].str.contains(text, case=False, regex=False)]
if review_only:
    f = f[(f["confidence"] < api.REVIEW_THRESHOLD) & (f["category_source"] != "user")]

# ---------------- metrics ----------------
spent, received = f.loc[f.type == "debit", "amount"].sum(), f.loc[f.type == "credit", "amount"].sum()
n_review = int(((df["confidence"] < api.REVIEW_THRESHOLD) & (df["category_source"] != "user")).sum())
c1, c2, c3, c4 = st.columns(4)
c1.metric("Transactions (filtered)", f"{len(f):,}", f"of {len(df):,}", delta_color="off")
c2.metric("Spent", f"₹{spent:,.0f}")
c3.metric("Received", f"₹{received:,.0f}")
c4.metric("Need review", n_review, help="Low-confidence ML predictions worth checking")

# ---------------- tabs ----------------
tab_dash, tab_tx, tab_anom, tab_subs, tab_fc, tab_cat, tab_month, tab_budget, tab_ask = st.tabs(
    ["Dashboard", "Transactions", "Anomalies", "Subscriptions", "Forecast", "By category", "Monthly spend", "Budgets", "Ask"])

with tab_budget:
    budgets_ui.render(df, DB_PATH, forecast_result=forecast_result)

with tab_ask:
    chat_ui.render(df, db.load_budgets(DB_PATH),
                   precomputed_anomalies=anomaly_result,
                   precomputed_recurring=recurring_result,
                   precomputed_forecast=forecast_result)

with tab_dash:
    dashboard.render(f, df, anomaly_result=anomaly_result, recurring_result=recurring_result)

with tab_tx:
    view = f.assign(date=f["date"].dt.date, confidence=f["confidence"].round(2))
    st.dataframe(
        view[["id", "date", "description", "amount", "type", "category", "confidence", "category_source"]],
        width="stretch", height=450, hide_index=True,
        column_config={"amount": st.column_config.NumberColumn(format="₹%.2f"),
                       "confidence": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    st.download_button("Download filtered CSV", f.drop(columns=["id"]).to_csv(index=False), "transactions.csv", "text/csv")
    insights.render_review(f, df, DB_PATH, retrain=not HOSTED)

with tab_anom:
    insights.render_anomalies(f, df, anomaly_result=anomaly_result)

with tab_subs:
    insights.render_subscriptions(df, recurring_result=recurring_result)

with tab_fc:
    insights.render_forecast(df, forecast_result=forecast_result)

with tab_cat:
    spend = f[f["type"] == "debit"].groupby("category", as_index=False)["amount"].sum().sort_values("amount")
    if spend.empty:
        st.info("No debit transactions in the current filter.")
    else:
        st.plotly_chart(px.bar(spend, x="amount", y="category", orientation="h", title="Spending by category"), width="stretch")

with tab_month:
    m = f[f["type"] == "debit"].assign(month=lambda d: d["date"].dt.to_period("M").astype(str))
    monthly = m.groupby("month", as_index=False)["amount"].sum()
    if monthly.empty:
        st.info("No debit transactions in the current filter.")
    else:
        st.plotly_chart(px.bar(monthly, x="month", y="amount", title="Monthly spending"), width="stretch")
