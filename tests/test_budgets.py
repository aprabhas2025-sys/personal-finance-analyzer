import math

import pandas as pd
import pytest

from app import budgets as B, charts, chatbot, db
from app.chat_tools import ChatTools
from tests.test_chatbot import FakeApi


def _tx(rows):
    return pd.DataFrame(rows, columns=["date", "description", "amount", "type", "category"]).assign(date=lambda d: pd.to_datetime(d["date"]))


def _df():
    """Jan, Feb, Mar complete (ends 31 Mar). Dining: 1000/1000/1500. Groceries: 2000/2000/500."""
    rows = []
    for m, (d, g) in zip(["2026-01", "2026-02", "2026-03"], [(1000, 2000), (1000, 2000), (1500, 500)]):
        rows += [(f"{m}-02", "UPI/SWIGGY/1", d, "debit", "Dining Out"), (f"{m}-10", "UPI/BIGBASKET/1", g, "debit", "Groceries"),
                 (f"{m}-28" if m != "2026-03" else "2026-03-31", "SALARY", 50000, "credit", "Income")]
    return _tx(rows).assign(id=lambda d: range(1, len(d) + 1))


FC = pd.DataFrame({"category": ["Dining Out", "Groceries"], "forecast_amount": [1200.0, 1500.0]})


def test_status_logic_over_will_exceed_near_ok():
    t, meta = B.status_table(_df(), {"Dining Out": 1200, "Groceries": 1000}, FC)
    s = t.set_index("category")
    assert meta == {"month": "2026-03", "partial": False}
    assert s.loc["Dining Out", "spent"] == 1500 and s.loc["Dining Out", "status"] == "over"
    assert s.loc["Groceries", "status"] == "will exceed" and s.loc["Groceries", "forecast"] == 1500.0     # March 500 is fine, forecast 1500 > 1000
    t2, _ = B.status_table(_df(), {"Groceries": 600}, FC.assign(forecast_amount=[0.0, 100.0]))
    assert t2.iloc[0]["status"] == "near limit" and t2.iloc[0]["pct_used"] == pytest.approx(500 / 600, abs=1e-3)   # 83% used
    t3, _ = B.status_table(_df(), {"Groceries": 5000}, FC)
    assert t3.iloc[0]["status"] == "ok"


def test_sorted_by_most_used_first_and_missing_forecast_is_ok():
    t, _ = B.status_table(_df(), {"Dining Out": 10000, "Groceries": 600}, None)
    assert list(t["category"]) == ["Groceries", "Dining Out"] and t["forecast"].isna().all()


def test_empty_inputs_and_bad_limits():
    for args in [(_df(), {}), (_df().iloc[0:0], {"Dining Out": 100}), (None, {"x": 1}), (_df(), {"Dining Out": 0}), (_df(), {"Dining Out": None})]:
        t, meta = B.status_table(*args)
        assert t.empty and list(t.columns) == B.COLUMNS and meta["month"] is None


def test_partial_latest_month_is_flagged():
    df = _df()
    df = df[df["date"] <= "2026-03-15"]                                       # statement ends mid-March
    _, meta = B.status_table(df, {"Dining Out": 100}, FC)
    assert meta == {"month": "2026-03", "partial": True}


def test_suggest_uses_complete_months_with_margin_and_rounding():
    s = B.suggest(_df())
    assert s["Dining Out"] == math.ceil(1166.67 * 1.1 / 100) * 100 and s["Groceries"] == math.ceil(1500 * 1.1 / 100) * 100
    assert "Income" not in s
    partial = _df()[lambda d: d["date"] <= "2026-03-12"]                      # drop the unfinished March: Jan+Feb only
    assert B.suggest(partial)["Dining Out"] == 1100 and B.suggest(_df().iloc[0:0]) == {}


def test_budget_storage_roundtrip_filters_bad_values_and_clear(tmp_path):
    p = tmp_path / "t.db"
    assert db.load_budgets(p) == {}
    assert db.save_budgets({"Dining Out": 1500, "Fuel": 0, "Health": -5, "Rent": None, "Misc": float("nan"), "Edu": "abc", "Groceries": "2500"}, p) == 2
    assert db.load_budgets(p) == {"Dining Out": 1500.0, "Groceries": 2500.0}
    db.save_budgets({"Fuel": 800}, p)                                           # replaces, not merges
    assert db.load_budgets(p) == {"Fuel": 800.0}
    db.clear(p)
    assert db.load_budgets(p) == {}


def test_budgets_are_per_session(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "f.db")
    a, b = db.session_path("aa11"), db.session_path("bb22")
    db.save_budgets({"Fuel": 1}, a)
    assert db.load_budgets(b) == {}


def test_chat_tool_and_rules_answer_budget_questions():
    tools = ChatTools(_df(), api=FakeApi(), budgets={"Dining Out": 1200})
    r = tools.run("budget_status")
    assert r["month"] == "2026-03" and r["budgets"][0]["status"] == "over" and r["budgets"][0]["percent_used"] == 125.0
    out = chatbot.answer("Am I over budget?", [], tools)
    assert "Dining Out" in out["text"] and "over" in out["text"] and out["tool_calls"] == ["budget_status"]
    none = chatbot.answer("any budget alerts?", [], ChatTools(_df(), api=FakeApi()))
    assert "haven't set any budgets" in none["text"]


def test_budget_chart_colours_and_empty():
    t, _ = B.status_table(_df(), {"Dining Out": 1200, "Groceries": 5000}, FC)
    fig = charts.fig_budget(t, "2026-03")
    assert fig.layout.paper_bgcolor == charts.CLEAR and len(fig.data) == 2     # transparent: the chart sits on a glass card
    assert dict(zip(fig.data[1].y, fig.data[1].marker.color))["Dining Out"] == charts.SPEND
    assert charts.fig_budget(pd.DataFrame(columns=B.COLUMNS)) is None


def test_budgets_tab_renders_saves_and_flags(tmp_path):
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    import os
    import tempfile
    from pathlib import Path
    script = Path(tempfile.mkdtemp()) / "budget_app.py"
    root = Path(__file__).resolve().parent.parent
    script.write_text(
        f"import sys; sys.path.insert(0, {str(root)!r})\n"
        "import pandas as pd\nfrom pathlib import Path\nfrom app import budgets_ui, db\n"
        "from tests.test_budgets import _df, FC\nfrom tests.test_chatbot import FakeApi\n"
        "budgets_ui._forecast = lambda full: FakeApi().forecast(full)\n"
        f"P = Path({str(tmp_path / 'b.db')!r})\n"
        "budgets_ui.render(_df(), P)\n", encoding="utf-8")
    at = AppTest.from_file(str(script), default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("No budgets saved yet" in i.value for i in at.info)                       # first render: nothing saved yet
    assert [b.label for b in at.button] == ["Save budgets", "Suggest from my average"]
    at.button[1].click().run()                                                           # suggest -> editor reseeded
    assert not at.exception, [e.value for e in at.exception]
    at.button[0].click().run()                                                           # save the suggested limits
    assert not at.exception, [e.value for e in at.exception]
    saved = db.load_budgets(tmp_path / "b.db")
    assert saved["Dining Out"] == 1300.0 and saved["Groceries"] == 1700.0
    assert {m.label for m in at.metric} >= {"Month", "Over budget now", "Forecast to exceed next month"}
