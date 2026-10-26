from app import theme


def test_css_loads_is_balanced_and_has_no_blank_lines():
    c = theme.css()
    assert len(c) > 1000 and c.count("{") == c.count("}")
    assert "\n\n" not in c                                         # a blank line can end the HTML block in Markdown
    assert "prefers-reduced-motion" in c and "max-width: 760px" in c   # motion and phone rules are present


def test_css_uses_role_selectors_so_it_survives_streamlit_dom_changes():
    c = theme.css()
    assert '[role="tab"]' in c and '[role="tablist"]' in c and '.stTabs [data-baseweb' not in c


def test_hero_component_contains_full_viewport_spline_scene():
    h = theme.HERO_HTML
    assert "\n" not in h and h.startswith('<div class="fa-hero-root"')
    assert h.count("<div") == h.count("</div>")
    assert "https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode" in h
    assert "events-target=\"global\"" in h and "load-complete" in h
    assert "prefers-reduced-motion" in h and "fa-live" in h and "fa-cursor-glow" in h
    assert all(section in h for section in ("fa-overview", "fa-insights", "fa-planning", "fa-privacy", "fa-start"))
    assert "animation-timeline:view()" in h and "unloadable" in h


def test_hero_makes_no_fake_numbers():
    import re
    visible = re.sub(r"<style>.*?</style>|<script.*?</script>", "", theme.HERO_HTML, flags=re.S)
    assert not re.search(r"[₹$]\s?\d|\d+%", visible)  # no made-up balances or percentages


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
    assert "<style>" in html and "fa-hero-root" in theme.HERO_HTML
