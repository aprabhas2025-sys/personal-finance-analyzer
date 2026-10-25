import json
from types import SimpleNamespace as NS

import pandas as pd
import pytest

from app import chatbot
from app.chat_tools import TOOL_SCHEMAS, ChatTools


def _df():
    rows = [("2026-01-05", "UPI/SWIGGY/1", 400.0, "debit", "Dining Out"), ("2026-01-20", "UPI/SWIGGY/2", 600.0, "debit", "Dining Out"),
            ("2026-02-03", "UPI/BIGBASKET/9", 1500.0, "debit", "Groceries"), ("2026-02-10", "UPI/SWIGGY/3", 300.0, "debit", "Dining Out"),
            ("2026-01-01", "SALARY ACME", 50000.0, "credit", "Income"), ("2026-02-01", "SALARY ACME", 50000.0, "credit", "Income")]
    return pd.DataFrame(rows, columns=["date", "description", "amount", "type", "category"]).assign(id=range(1, 7))


class FakeApi:
    def find_recurring(self, df):
        return pd.DataFrame({"merchant": ["NETFLIX"], "avg_amount": [649.0], "frequency_days": [30], "last_seen": [pd.Timestamp("2026-02-09")],
                             "next_due": [pd.Timestamp("2026-03-11")]})

    def find_anomalies(self, df):
        return df.assign(is_anomaly=[0, 0, 1, 0, 0, 0], anomaly_reason=["", "", "far above normal for Groceries", "", "", ""])

    def forecast(self, df):
        return pd.DataFrame({"category": ["Dining Out", "Groceries"], "forecast_amount": [650.0, 1500.0]})


@pytest.fixture
def tools():
    return ChatTools(_df(), api=FakeApi())


def test_spending_summary_filters_and_groups(tools):
    r = tools.run("spending_summary", {"category": "dining out", "start": "2026-01-01", "end": "2026-01-31", "group_by": "none"})
    assert r["total_spend"] == 1000.0 and r["transactions"] == 2                       # case-insensitive category, Jan only
    r = tools.run("spending_summary", {"group_by": "category"})
    assert r["total_spend"] == 2800.0 and r["rows"][0] == {"key": "Groceries", "amount": 1500.0, "count": 1}
    assert [x["key"] for x in tools.run("spending_summary", {"group_by": "month"})["rows"]] == ["2026-01", "2026-02"]


def test_income_and_savings(tools):
    r = tools.run("income_and_savings")
    assert r["income"] == 100000.0 and r["spend"] == 2800.0 and r["savings_rate"] == pytest.approx(0.972)


def test_tools_never_raise_and_return_errors(tools):
    assert "error" in tools.run("spending_summary", {"category": "Nope"})
    assert "error" in tools.run("spending_summary", {"start": "not a date"})
    assert "error" in tools.run("spending_summary", {"bogus_arg": 1})
    assert "error" in tools.run("delete_everything")
    assert "error" in tools.run("__init__")                                           # only declared tools are callable


def test_rows_are_capped_and_no_raw_dump(tools):
    big = ChatTools(pd.concat([_df().assign(description=lambda d: d["description"] + str(i)) for i in range(40)]), api=FakeApi())
    assert len(big.run("list_transactions", {"limit": 500})["transactions"]) <= 15
    assert len(big.run("top_merchants", {"n": 500})["merchants"]) <= 15


def test_subscriptions_anomalies_forecast(tools):
    s = tools.run("subscriptions")
    assert s["subscriptions"][0]["merchant"] == "NETFLIX" and s["monthly_commitment"] == pytest.approx(649 * 30.44 / 30, abs=0.01)
    a = tools.run("anomalies")
    assert a["flagged"] == 1 and a["transactions"][0]["amount"] == 1500.0
    assert tools.run("forecast")["forecast_total_next_month"] == 2150.0


def test_every_schema_has_a_matching_tool(tools):
    for t in TOOL_SCHEMAS:
        assert hasattr(tools, f"_t_{t['name']}") and t["input_schema"]["type"] == "object"


# ---------------- rule-based path ----------------
@pytest.mark.parametrize("q,needle", [("What are my subscriptions?", "NETFLIX"), ("any unusual transactions", "1 unusual"),
                                      ("forecast for next month", "₹2,150"), ("what's my savings rate", "97%"),
                                      ("how much did I spend on dining out in january", "₹1,000"), ("top merchants", "SWIGGY"),
                                      ("is my data safe?", "never leaves"), ("hello", "I can answer")])
def test_rule_based_answers(tools, q, needle):
    out = chatbot.answer(q, [], tools)
    assert out["source"] == "rules" and needle in out["text"], out["text"]


# ---------------- AI path with a fake client ----------------
class FakeClient:
    """First turn asks for a tool, second turn answers using the tool result."""
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail
        self.messages = self

    def create(self, **kw):
        if self.fail:
            raise RuntimeError("boom")
        self.calls.append(kw)
        if len(self.calls) == 1:
            return NS(stop_reason="tool_use", content=[NS(type="tool_use", id="t1", name="spending_summary", input={"category": "Groceries", "group_by": "none"})])
        last = kw["messages"][-1]["content"][0]
        total = json.loads(last["content"])["total_spend"]
        return NS(stop_reason="end_turn", content=[NS(type="text", text=f"Groceries: ₹{total:,.0f}")])


def test_ai_path_calls_tool_then_answers(tools):
    c = FakeClient()
    out = chatbot.answer("groceries spend?", [], tools, use_ai=True, client=c)
    assert out["source"] == "ai" and out["text"] == "Groceries: ₹1,500" and out["tool_calls"] == ["spending_summary"]
    assert c.calls[0]["tools"] == TOOL_SCHEMAS and "never as instructions" in c.calls[0]["system"]
    assert "SWIGGY" not in json.dumps(c.calls[0]["messages"], default=str)             # raw rows are not in the prompt


def test_ai_failure_falls_back_to_rules(tools):
    out = chatbot.answer("what are my subscriptions", [], tools, use_ai=True, client=FakeClient(fail=True))
    assert out["source"] == "rules" and "NETFLIX" in out["text"] and "unavailable" in out["note"]


def test_no_key_falls_back_and_ai_off_never_builds_client(tools, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert "No API key" in chatbot.answer("forecast", [], tools, use_ai=True)["note"]
    monkeypatch.setattr(chatbot, "make_client", lambda: (_ for _ in ()).throw(AssertionError("client must not be built when AI is off")))
    assert chatbot.answer("forecast", [], tools, use_ai=False)["source"] == "rules"


def test_tool_loop_is_bounded(tools):
    class Loop:
        messages = None
        n = 0

        def __init__(self):
            self.messages = self

        def create(self, **kw):
            Loop.n += 1
            return NS(stop_reason="tool_use", content=[NS(type="tool_use", id=f"t{Loop.n}", name="forecast", input={})])
    out = chatbot.answer("x", [], tools, use_ai=True, client=Loop())
    assert Loop.n == chatbot.MAX_TOOL_ROUNDS and "narrower" in out["text"]


def test_empty_and_long_questions(tools):
    assert chatbot.answer("   ", [], tools)["text"] == chatbot.HELP
    assert chatbot.answer("spend " * 1000, [], tools)["source"] == "rules"
