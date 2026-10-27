from app import theme


def test_css_loads_is_balanced_and_has_no_blank_lines():
    c = theme.css()
    assert len(c) > 1000 and c.count("{") == c.count("}")
    assert "\n\n" not in c                                         # a blank line can end the HTML block in Markdown
    assert "prefers-reduced-motion" in c and "max-width: 760px" in c   # motion and phone rules are present


def test_css_uses_role_selectors_so_it_survives_streamlit_dom_changes():
    c = theme.css()
    assert '[role="tab"]' in c and '[role="tablist"]' in c and '.stTabs [data-baseweb' not in c


def test_hero_html_is_safe_for_markdown():
    h = theme.HERO_HTML
    assert "\n" not in h and h.startswith("<div") and h.count("<div") == h.count("</div>")
    assert "<script" not in h.lower() and "<img" not in h.lower()          # no remote or cartoon images, no scripts


def test_hero_makes_no_fake_numbers():
    import re
    assert not re.search(r"[₹$]\s?\d|\d+%", theme.HERO_HTML)               # a decorative panel must not show invented figures


def test_missing_stylesheet_does_not_break_the_app(monkeypatch, tmp_path):
    monkeypatch.setattr(theme, "CSS_PATH", tmp_path / "nope.css")
    assert theme.css() == ""
    theme.inject()                                                          # no Streamlit runtime here: must still not raise


def test_theme_renders_in_a_streamlit_run():
    import pytest
    AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
    at = AppTest.from_string("from app import theme\ntheme.inject()\ntheme.hero()").run()
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "fa-hero" in html and "<style>" in html
