"""Streamlit app. Run from the project root:  streamlit run app/app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from app.cleaning import CleaningError, clean_transactions
from ml import api

st.set_page_config(page_title="Personal Finance Analyzer", page_icon="💸", layout="wide")
st.title("💸 Personal Finance Analyzer")
st.caption("Upload a bank/UPI statement CSV. Everything runs locally and your data never leaves this machine.")

SAMPLE = ROOT / "data" / "synthetic_bank_export.csv"

with st.sidebar:
    st.header("1. Load data")
    up = st.file_uploader("Bank statement (CSV)", type=["csv"])
    use_sample = st.button("Use sample data", disabled=not SAMPLE.exists())
    if use_sample:
        st.session_state["sample"] = True
    if up is not None:
        st.session_state["sample"] = False

raw = None
if up is not None:
    raw = pd.read_csv(up, dtype=str)
elif st.session_state.get("sample"):
    raw = pd.read_csv(SAMPLE, dtype=str)

if raw is None:
    st.info("Upload a CSV or click **Use sample data** in the sidebar to begin.")
    st.stop()

try:
    df, report = clean_transactions(raw)
except CleaningError as e:
    st.error(str(e))
    st.stop()

df = api.categorize(df)      # Person A's model plugs in here

c1, c2, c3, c4 = st.columns(4)
c1.metric("Transactions", f"{report['rows_out']:,}")
c2.metric("Total spent", f"₹{report['total_debit']:,.0f}")
c3.metric("Total received", f"₹{report['total_credit']:,.0f}")
c4.metric("Rows dropped", report["rows_dropped"])
lo, hi = report["date_range"]
st.caption(f"{lo:%d %b %Y} to {hi:%d %b %Y}")

tab_tx, tab_chart = st.tabs(["Transactions", "Monthly spend"])
with tab_tx:
    st.dataframe(df.assign(date=df["date"].dt.date), width="stretch", height=450)
with tab_chart:
    spend = df[df["type"] == "debit"].assign(month=lambda d: d["date"].dt.to_period("M").astype(str))
    monthly = spend.groupby("month", as_index=False)["amount"].sum()
    st.plotly_chart(px.bar(monthly, x="month", y="amount", title="Monthly spending"), width="stretch")
