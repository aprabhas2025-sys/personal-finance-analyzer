"""Visual theme: injects app/style.css and renders the hero banner. Styling only; it never touches data and never breaks the app."""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

CSS_PATH = Path(__file__).with_name("style.css")

def _svg(body):
    return ('<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')


_FEATURES = [
    ("Smart categorisation", "Rules plus a small ML model sort every transaction. Low-confidence ones are flagged so you can correct them.",
     '<path d="M3 12V4h8l9 9-8 8-9-9z"/><circle cx="7.5" cy="8.5" r="1.2"/>'),
    ("Unusual-charge alerts", "Spots duplicate charges and amounts far above what is normal for their category. A prompt to check, not proof.",
     '<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5M12 18v.5"/>'),
    ("Subscriptions and bills", "Finds payments that repeat on a schedule and shows your monthly commitment and next due dates.",
     '<path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 013-3h15"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 01-3 3H3"/>'),
    ("Budgets with early warnings", "Set monthly limits per category and see what is over, near the limit, or forecast to exceed next month.",
     '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>'),
    ("Next-month forecast", "A simple, tested forecast with a backtest on your own history, so you can see how much to trust it.",
     '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>'),
    ("Ask in plain English", "A built-in assistant answers questions about your statement and about how the app works.",
     '<path d="M21 12a8 8 0 01-11.6 7.1L3 21l1.9-5.4A8 8 0 1121 12z"/>'),
]

HERO_PATH = Path(__file__).with_name("hero.html")
HERO_HTML = HERO_PATH.read_text(encoding="utf-8").replace("\r", "").replace("\n", "")
_LOGIN_COMPONENT = components.declare_component("finora_login_page", path=str(Path(__file__).with_name("login_component")))
BRAND_HTML = ('<div class="fa-brand"><span class="fa-logo" aria-hidden="true">F</span><span>Finora</span>'
              '<svg class="fa-brand-mark" viewBox="0 0 24 24" aria-label="Financial insights" role="img" '
              'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M4 17.5 9 12l3.5 3.5L20 7.5"/><path d="M14.5 7.5H20V13"/>'
              '<circle cx="12" cy="12" r="10.5"/></svg></div>')

FEATURES_HTML = (
    '<div class="fa-section-head"><small>Features</small><h2>Everything your statement can tell you</h2></div><div class="fa-grid">'
    + "".join(f'<div class="fa-card"><div class="fa-ico">{_svg(icon)}</div><h3>{t}</h3><p>{d}</p></div>' for t, d, icon in _FEATURES)
    + '</div>'
)

STEPS_HTML = (
    '<div class="fa-section-head"><small>How it works</small><h2>From statement to insight in three steps</h2></div><div class="fa-steps">'
    '<div class="fa-step"><b>1</b><h3>Create an account</h3><p>Sign up with your email. Your data is kept apart from every other account.</p></div>'
    '<div class="fa-step"><b>2</b><h3>Upload a statement</h3><p>Drop in a bank or UPI CSV, or load the built-in sample to look around first.</p></div>'
    '<div class="fa-step"><b>3</b><h3>Explore and correct</h3><p>Browse the dashboard, fix any wrong category, set budgets and ask questions.</p></div>'
    '</div>'
)

TRUST_HTML = (
    '<div class="fa-trust"><div><small>Honest by design</small><h3>Numbers you can check</h3>'
    '<p>Accuracy figures in the project README are measured on synthetic data and labelled that way. Anomaly flags and forecasts are prompts to check, not financial advice.</p></div>'
    '<div><small>Your data</small><h3>Private to your account</h3>'
    '<p>Passwords are stored only as salted hashes. Each account keeps its statement in its own file, and you can clear it or delete the account from the sidebar. '
    'On a hosted demo that file lives on the server, so use the sample data unless you trust the host or run the app yourself.</p></div></div>'
)

FOOTER_HTML = '<div class="fa-footer">Finora &middot; a personal finance workspace &middot; not financial advice</div>'


def css() -> str:
    """The stylesheet with blank lines removed (a blank line can end an HTML block in Markdown). Empty string if the file is missing."""
    try:
        text = CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
    return "\n".join(line for line in text.splitlines() if line.strip())


def inject():
    c = css()
    if c:
        st.markdown(f"<style>{c}</style>", unsafe_allow_html=True)


def html(block: str):
    st.markdown(block, unsafe_allow_html=True)


def hero(hosted=False):
    components.html(HERO_HTML.replace("<!--HOSTED_NOTICE-->", '<div class="fa-hosted-note">Hosted demo — use the built-in sample data unless you trust the host.</div>' if hosted else ""), height=900, scrolling=True)




def login_page(error=None):
    """Render the supplied login page and receive its sign-in/back actions."""
    return _LOGIN_COMPONENT(error=error, default=None, key="finora_login")
