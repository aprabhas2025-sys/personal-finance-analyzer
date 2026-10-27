import re

import pytest

from app import auth, config, db, theme

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
GATE = "import streamlit as st\nfrom app import landing\nu = landing.require_login()\nst.write('HOME ' + u['email'])\n"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DB_DIR", str(tmp_path))
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("FINANCE_HOSTED", raising=False)


def _btn(at, label):
    return next(b for b in at.button if b.label == label)


def _home(at):
    return any("HOME" in m.value for m in at.markdown)


def _fill(at, *values):
    for box, v in zip(at.text_input, values):
        box.set_value(v)


def test_signed_out_user_sees_landing_not_the_app():
    at = AppTest.from_string(GATE).run()
    assert not at.exception and not _home(at)
    assert {b.label for b in at.button} >= {"Sign in", "Get started", "Create free account"}
    page = " ".join(m.value for m in at.markdown)
    assert "fa-hero" in page and "fa-grid" in page and "fa-steps" in page and "<style>" in page


def test_signed_in_user_goes_straight_to_the_app_with_no_landing_markup():
    at = AppTest.from_string(GATE)
    at.session_state["user"] = {"id": "ab12", "email": "me@example.com"}
    at.run()
    assert _home(at) and not any("fa-hero" in m.value or "<style>" in m.value for m in at.markdown)   # plain Streamlit inside the app


def test_signup_then_lands_on_home():
    at = AppTest.from_string(GATE).run()
    _btn(at, "Get started").click().run()
    assert len(at.text_input) == 3                                    # email, password, confirm
    _fill(at, "new@example.com", "s3cret-pass", "s3cret-pass")
    _btn(at, "Create account").click().run()
    assert not at.exception and _home(at) and "new@example.com" in " ".join(m.value for m in at.markdown)
    assert at.session_state["user"]["email"] == "new@example.com"
    assert auth.authenticate("new@example.com", "s3cret-pass")[0] is not None            # really stored


def test_signup_errors_keep_you_on_the_form():
    at = AppTest.from_string(GATE).run()
    _btn(at, "Create free account").click().run()
    _fill(at, "bad-email", "s3cret-pass", "s3cret-pass")
    _btn(at, "Create account").click().run()
    assert not _home(at) and any("valid email" in e.value for e in at.error)
    _fill(at, "a@b.co", "s3cret-pass", "mismatch!!")
    _btn(at, "Create account").click().run()
    assert not _home(at) and any("do not match" in e.value for e in at.error)


def test_signin_success_and_failure():
    auth.create_user("a@b.co", "s3cret-pass")
    at = AppTest.from_string(GATE).run()
    _btn(at, "Sign in").click().run()
    assert len(at.text_input) == 2
    _fill(at, "a@b.co", "wrong-pass1")
    _btn(at, "Sign in").click().run()
    assert not _home(at) and any(auth.BAD_LOGIN in e.value for e in at.error) and "user" not in at.session_state
    _fill(at, "A@B.co", "s3cret-pass")
    _btn(at, "Sign in").click().run()
    assert _home(at) and at.session_state["user"]["email"] == "a@b.co"


def test_navigation_between_landing_signin_signup_and_back():
    at = AppTest.from_string(GATE).run()
    _btn(at, "Sign in").click().run()
    _btn(at, "New here? Create an account").click().run()
    assert len(at.text_input) == 3
    _btn(at, "Already have an account? Sign in").click().run()
    assert len(at.text_input) == 2
    _btn(at, "← Back").click().run()
    assert {b.label for b in at.button} >= {"Get started"} and not at.text_input


def test_password_fields_are_masked():
    at = AppTest.from_string(GATE).run()
    _btn(at, "Get started").click().run()
    assert [t.proto.type for t in at.text_input] == [0, 1, 1]            # 0 = plain text, 1 = masked password


def test_landing_html_is_markdown_safe_and_honest():
    for block in (theme.HERO_HTML, theme.FEATURES_HTML, theme.STEPS_HTML, theme.TRUST_HTML, theme.FOOTER_HTML, theme.BRAND_HTML):
        assert "\n" not in block and block.count("<div") == block.count("</div>")
        assert "<script" not in block.lower() and "<img" not in block.lower() and "http" not in block.lower()
        assert not re.search(r"[₹$]\s?\d|\d+\s?%", block)            # no invented figures, prices or stats
    assert theme.FEATURES_HTML.count('class="fa-card"') == 6 and "testimonial" not in theme.FEATURES_HTML.lower()


def test_hosted_notice_on_landing(monkeypatch):
    monkeypatch.setenv("FINANCE_HOSTED", "1")
    at = AppTest.from_string(GATE).run()
    assert any("hosted demo" in c.value for c in at.caption)
    assert "account" in config.HOSTED_CAPTION and "never leaves" not in config.HOSTED_CAPTION
