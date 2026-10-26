from pathlib import Path

import pytest

from app import db

APP = Path(__file__).resolve().parent.parent / "app" / "app.py"


def test_streamlit_app_all_tabs_render(tmp_path, monkeypatch):
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "app.db")
    at = AppTest.from_file(str(APP), default_timeout=90)
    at.session_state["user"] = {"id": "ab12cd34", "email": "t@example.com"}      # signed in
    at.run()
    next(b for b in at.sidebar.button if b.label == "Use sample data").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert [t.label for t in at.tabs] == ["Dashboard", "Transactions", "Anomalies", "Subscriptions", "Forecast", "By category", "Monthly spend", "Budgets", "Ask"]
    m = {x.label: x.value for x in at.metric}
    assert m["Monthly commitment"].startswith("₹") and m["Months of history"] == "12"
    assert any(k.startswith("Forecast spend") for k in m)
    assert m["Method"] == "mean all"
    assert "Total amount flagged" in m
    assert any("Review & correct" in e.label for e in at.expander)
