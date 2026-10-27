"""'Budgets' tab: set a monthly limit per category, see spent vs limit and which categories are forecast to exceed it."""
import pandas as pd
import streamlit as st

from app import budgets as B, charts, db

_RS = st.column_config.NumberColumn(format="₹%.0f")
_ICON = {"over": "🔴 over", "will exceed": "🟠 will exceed", "near limit": "🟡 near limit", "ok": "🟢 ok"}


def render(full: pd.DataFrame, db_path=None, forecast_result: pd.DataFrame = None):
    cats = sorted(full.loc[full["type"] == "debit", "category"].unique())
    if not cats:
        st.info("No debit transactions to budget against.")
        return
    saved = db.load_budgets(db_path)
    n = st.session_state.setdefault("budget_n", 0)
    seed = st.session_state.get("budget_seed") or saved          # suggestions stay until saved, so Save after Suggest keeps them
    editor_src = pd.DataFrame({"category": cats, "monthly_limit": [float(seed.get(c, 0.0)) for c in cats]})

    st.caption("Set a monthly limit for the categories you care about (leave 0 for no budget). Your limits are stored only in this session.")
    edited = st.data_editor(editor_src, key=f"budget_editor_{n}", hide_index=True, width="stretch", disabled=["category"],
                            column_config={"monthly_limit": st.column_config.NumberColumn("Monthly limit", min_value=0.0, step=100.0, format="₹%.0f")})
    a, b, _ = st.columns([1, 2, 4])
    if a.button("Save budgets", type="primary"):
        db.save_budgets(dict(zip(edited["category"], edited["monthly_limit"])), db_path)
        st.session_state.pop("budget_seed", None)
        st.session_state["budget_n"] = n + 1
        st.rerun()
    if b.button("Suggest from my average"):
        st.session_state["budget_seed"] = B.suggest(full)
        st.session_state["budget_n"] = n + 1
        st.rerun()

    if not saved:
        st.info("No budgets saved yet. Click *Suggest from my average*, adjust, then *Save budgets*.")
        return

    # Use pre-computed forecast if available
    fc = forecast_result
    if fc is None:
        try:
            from ml import api
            fc = api.forecast(full.drop(columns=["id"], errors="ignore"))
        except Exception:
            fc = None

    table, meta = B.status_table(full, saved, fc)
    bad = table[table["status"].isin(["over", "will exceed"])]
    c1, c2, c3 = st.columns(3)
    c1.metric("Month", meta["month"] + (" (so far)" if meta["partial"] else ""))
    c2.metric("Over budget now", int((table["status"] == "over").sum()))
    c3.metric("Forecast to exceed next month", int((table["status"] == "will exceed").sum()))
    if not bad.empty:
        st.warning("Needs attention: " + ", ".join(f"{r.category} ({_ICON[r.status].split(' ', 1)[1]})" for r in bad.itertuples()))
    fig = charts.fig_budget(table, meta["month"])
    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    view = table.assign(pct_used=table["pct_used"], status=table["status"].map(_ICON))
    st.dataframe(view.rename(columns={"spent": "spent (month)", "forecast": "forecast (next month)"}), width="stretch", hide_index=True,
                 column_config={"limit": _RS, "spent (month)": _RS, "forecast (next month)": _RS,
                                "pct_used": st.column_config.ProgressColumn("used", min_value=0, max_value=1.5, format="percent")})
    st.caption("'Over' compares the latest month in your statement with the limit. 'Will exceed' compares the next-month forecast "
               "(average of past months) with the limit. The forecast is a rough guide, not a promise.")
