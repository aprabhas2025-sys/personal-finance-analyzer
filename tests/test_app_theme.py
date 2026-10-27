"""In-app glass theme: stylesheet hygiene, landing isolation, and safe rendering. Styling only; no data is touched."""
import re

import pytest

from app import landing, theme

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
GATE = "import streamlit as st\nfrom app import landing\nu = landing.require_login()\nst.write('HOME ' + u['email'])\n"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DB_DIR", str(tmp_path))
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("FINANCE_HOSTED", raising=False)


def _page(at):
    return " ".join(m.value for m in at.markdown)


def test_app_css_is_balanced_markdown_safe_and_responsive():
    c = theme.app_css()
    assert len(c) > 5000 and c.count("{") == c.count("}")
    assert "\n\n" not in c                                          # a blank line can end the HTML block in Markdown
    assert "max-width: 760px" in c and "max-width: 991px" in c      # phone and tablet rules
    assert "prefers-reduced-motion" in c


def test_app_css_uses_stable_hooks_not_emotion_class_names():
    c = theme.app_css()
    assert "st-emotion-cache" not in c and '[role="tab"]' in c and '[role="tablist"]' in c


def test_app_css_has_an_icon_for_each_of_the_nine_tabs():
    c = theme.app_css()
    for i in range(1, 10):
        assert f'[role="tab"]:nth-child({i}) {{ --ico:' in c


def test_missing_app_stylesheet_does_not_break_the_app(monkeypatch, tmp_path):
    monkeypatch.setattr(theme, "APP_CSS_PATH", tmp_path / "nope.css")
    assert theme.app_css() == ""
    theme.inject_app()                                              # no Streamlit runtime: must not raise


def test_user_chip_escapes_the_email():
    h = theme.user_chip_html('<img src=x onerror=alert(1)>@evil.com')
    assert "<img" not in h and "&lt;img" in h and "\n" not in h


def test_page_header_escapes_text():
    h = theme.page_header_html("a", "<script>x</script>", "b & c")
    assert "<script>" not in h and "&amp;" in h


def test_landing_page_does_not_load_the_app_theme():
    at = AppTest.from_string(GATE).run()
    assert not at.exception
    page = _page(at)
    assert "fa-hero" in page and "fa-auth-mark" not in page
    assert "--rail" not in page and "fa-user" not in page           # none of the in-app theme leaks onto the landing page


@pytest.mark.parametrize("button", ["Sign in", "Get started"])
def test_auth_screens_use_the_app_theme(button):
    at = AppTest.from_string(GATE).run()
    next(b for b in at.button if b.label == button).click().run()
    assert not at.exception
    page = _page(at)
    assert "--rail" in page and "fa-auth-mark" in page              # app theme injected + new auth card mark
    assert len(at.text_input) in (2, 3)                             # same fields as before


def test_signed_in_app_gets_the_theme_and_keeps_the_nine_tabs(tmp_path, monkeypatch):
    from pathlib import Path
    from app import db
    monkeypatch.setattr(db, "DEFAULT_PATH", tmp_path / "app.db")
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app" / "app.py"), default_timeout=90)
    at.session_state["user"] = {"id": "ab12cd34", "email": "t@example.com"}
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    page = _page(at)
    assert "--rail" in page and "fa-user" in page and "t@example.com" in page      # theme + user chip
    next(b for b in at.sidebar.button if b.label == "Use sample data").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert [t.label for t in at.tabs] == ["Dashboard", "Transactions", "Anomalies", "Subscriptions", "Forecast",
                                          "By category", "Monthly spend", "Budgets", "Ask"]
    assert "Financial overview" in _page(at) and "1,433 transactions" in _page(at)   # header shows real data, no invented numbers
    assert not re.search(r"fa-page-head.*\u20b9\s?\d", _page(at))
