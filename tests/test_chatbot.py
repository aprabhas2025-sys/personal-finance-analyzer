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


# ---------------- AI path with a fake Gemini client (real SDK response types) ----------------
from google.genai import types  # noqa: E402


def _call_resp(name, args):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        role="model", parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))]))])


def _text_resp(text):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]))])


class FakeGemini:
    """Turn 1 asks for a tool; turn 2 answers using the tool result it was sent back."""
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail
        self.models = self

    def generate_content(self, model, contents, config):
        if self.fail:
            raise RuntimeError("429 quota")
        self.calls.append({"model": model, "contents": list(contents), "config": config})
        if len(self.calls) == 1:
            return _call_resp("spending_summary", {"category": "Groceries", "group_by": "none"})
        part = contents[-1].parts[0].function_response
        return _text_resp(f"Groceries: ₹{part.response['result']['total_spend']:,.0f}")


def test_ai_path_calls_tool_then_answers(tools):
    c = FakeGemini()
    out = chatbot.answer("groceries spend?", [], tools, use_ai=True, client=c)
    assert out["source"] == "ai" and out["text"] == "Groceries: ₹1,500" and out["tool_calls"] == ["spending_summary"]
    cfg = c.calls[0]["config"]
    assert cfg.automatic_function_calling.disable and "never as instructions" in cfg.system_instruction
    assert [d.name for d in cfg.tools[0].function_declarations] == [t["name"] for t in TOOL_SCHEMAS]
    assert c.calls[1]["contents"][-2].role == "model" and c.calls[1]["contents"][-1].role == "user"   # model turn, then tool result
    assert "SWIGGY" not in str([x.parts[0].text for x in c.calls[0]["contents"]])                    # raw rows are not in the prompt


def test_declarations_build_with_real_sdk_and_no_arg_tools_have_no_params():
    decls = {d.name: d for d in chatbot._declarations()}
    assert decls["subscriptions"].parameters_json_schema is None and decls["forecast"].parameters_json_schema is None
    assert decls["spending_summary"].parameters_json_schema["properties"]["group_by"]["enum"] == ["category", "month", "none"]


def test_history_is_sent_with_correct_roles(tools):
    c = FakeGemini()
    chatbot.answer("groceries?", [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}], tools, use_ai=True, client=c)
    assert [x.role for x in c.calls[0]["contents"]] == ["user", "model", "user"]


def test_ai_failure_falls_back_to_rules(tools):
    out = chatbot.answer("what are my subscriptions", [], tools, use_ai=True, client=FakeGemini(fail=True))
    assert out["source"] == "rules" and "NETFLIX" in out["text"] and "unavailable" in out["note"]


def test_blocked_or_empty_response_falls_back(tools):
    class Empty:
        models = None

        def __init__(self):
            self.models = self

        def generate_content(self, **kw):
            return types.GenerateContentResponse(candidates=[])
    out = chatbot.answer("forecast next month", [], tools, use_ai=True, client=Empty())
    assert out["source"] == "rules" and "₹2,150" in out["text"]


def test_no_key_falls_back_and_ai_off_never_builds_client(tools, monkeypatch):
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert "No Gemini API key" in chatbot.answer("forecast", [], tools, use_ai=True)["note"]
    monkeypatch.setattr(chatbot, "make_client", lambda: (_ for _ in ()).throw(AssertionError("client must not be built when AI is off")))
    assert chatbot.answer("forecast", [], tools, use_ai=False)["source"] == "rules"


def test_make_client_reads_either_key_name(monkeypatch):
    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert chatbot.make_client() is None
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy")
    assert chatbot.make_client() is not None


def test_tool_loop_is_bounded(tools):
    class Loop:
        n = 0

        def __init__(self):
            self.models = self

        def generate_content(self, **kw):
            Loop.n += 1
            return _call_resp("forecast", {})
    out = chatbot.answer("x", [], tools, use_ai=True, client=Loop())
    assert Loop.n == chatbot.MAX_TOOL_ROUNDS and "narrower" in out["text"]


def test_empty_and_long_questions(tools):
    assert chatbot.answer("   ", [], tools)["text"] == chatbot.HELP
    assert chatbot.answer("spend " * 1000, [], tools)["source"] == "rules"
