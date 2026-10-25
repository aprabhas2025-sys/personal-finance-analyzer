"""Streamlit app. Run from the project root:  streamlit run app/app.py"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from app import dashboard, db
from app.cleaning import CleaningError, clean_transactions
from ml import api
from ml.schema import CATEGORIES

st.set_page_config(page_title="Personal Finance Analyzer", page_icon="💸", layout="wide")
st.title("💸 Personal Finance Analyzer")
st.caption("Upload a bank/UPI statement CSV. Everything runs locally and your data never leaves this machine.")

SAMPLE = ROOT / "data" / "synthetic_bank_export.csv"


def ingest(raw: pd.DataFrame):
    df, report = clean_transactions(raw)
    df = api.categorize(df)                    # Person A's model
    db.replace_all(df)
    st.session_state["report"] = report


# ---------------- sidebar: load data ----------------
with st.sidebar:
    st.header("1. Load data")
    up = st.file_uploader("Bank statement (CSV)", type=["csv"])
    use_sample = st.button("Use sample data", disabled=not SAMPLE.exists())
    if st.button("Clear stored data"):
        db.clear()
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

df = db.load()
if df.empty:
    st.info("Upload a CSV or click **Use sample data** in the sidebar to begin.")
    st.stop()

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
tab_dash, tab_tx, tab_cat, tab_month = st.tabs(["Dashboard", "Transactions", "By category", "Monthly spend"])

with tab_dash:
    dashboard.render(f, df)

with tab_tx:
    view = f.assign(date=f["date"].dt.date, confidence=f["confidence"].round(2))
    st.dataframe(
        view[["id", "date", "description", "amount", "type", "category", "confidence", "category_source"]],
        width="stretch", height=450, hide_index=True,
        column_config={"amount": st.column_config.NumberColumn(format="₹%.2f"),
                       "confidence": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.2f")})
    st.download_button("Download filtered CSV", f.drop(columns=["id"]).to_csv(index=False), "transactions.csv", "text/csv")

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
