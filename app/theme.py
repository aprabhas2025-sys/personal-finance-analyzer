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

HERO_HTML = (
    '<div class="fa-hero"><div class="fa-hero-inner">'
    '<div class="fa-hero-copy">'
    '<span class="fa-eyebrow"><i></i>Personal Finance Analyzer</span>'
    '<h1>Know exactly where your money <em>goes</em></h1>'
    '<p>Upload a bank or UPI statement and get clean categories, unusual-charge alerts, subscriptions, budgets and a next-month forecast, in one private workspace.</p>'
    '</div>'
    '<div class="fa-hero-card"><small>What you get</small>'
    '<div>Auto-categorised spending</div><div>Duplicate &amp; unusual charge alerts</div><div>Subscriptions and recurring bills</div>'
    '<div>Budgets with early warnings</div><div>Next-month forecast</div><div>Ask questions in plain English</div>'
    '</div></div></div>'
)

BRAND_HTML = '<div class="fa-brand"><span class="fa-logo"></span><span>Finance Analyzer</span></div>'

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

FOOTER_HTML = '<div class="fa-footer">Personal Finance Analyzer &middot; a portfolio project &middot; not financial advice</div>'


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


def inject_landing():
    """Replace the glass canvas with the dark, full-width 3D landing canvas."""
    st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
      background: #050506 !important;
      background-image: none !important;
      color: #f5f5f7 !important;
    }
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
    .block-container, [data-testid="stMainBlockContainer"] {
      width: 100% !important;
      max-width: none !important;
      margin: 0 !important;
      padding: 0 !important;
    }
    .st-key-fa_nav {
      width: min(1440px, 92vw) !important;
      margin: 0 auto !important;
      padding: 18px 0 !important;
    }
    .st-key-fa_nav .fa-brand { color: #f5f5f7 !important; }
    </style>
    """, unsafe_allow_html=True)


_HERO_COMPONENT = components.declare_component('finora_hero_page', path=str(Path(__file__).with_name('hero_component')))
_LOGIN_COMPONENT = components.declare_component("finora_login_page", path=str(Path(__file__).with_name("login_component")))


def login_page(mode="signin", error=None):
    """Render the tracked-light sign-in or account creation form."""
    st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
      background: #050506 !important; background-image: none !important; color: #f5f3fa !important;
    }
    header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], section[data-testid="stSidebar"] { display: none !important; }
    .block-container, [data-testid="stMainBlockContainer"] {
      width: 100% !important; max-width: none !important; margin: 0 !important; padding: 0 !important;
    }
    .st-key-fa_login { width: 100vw !important; max-width: none !important; margin: 0 !important; padding: 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    return _LOGIN_COMPONENT(mode=mode, error=error, default=None, key="finora_account")


def html(block: str):
    st.markdown(block, unsafe_allow_html=True)


def hero():
    """Render the interactive 3D landing component and return auth actions."""
    return _HERO_COMPONENT(default=None, key="finora_hero")


# ---------------------------------------------------------------------------------------------------------------------
# In-app glass theme (signed-in views + sign-in/sign-up). The landing page keeps using style.css above, untouched.
# ---------------------------------------------------------------------------------------------------------------------
APP_CSS_PATH = Path(__file__).with_name("style_app.css")


def app_css() -> str:
    """The in-app stylesheet with blank lines removed (same Markdown-safety rule as css()). Empty string if missing."""
    try:
        text = APP_CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
    return "\n".join(line for line in text.splitlines() if line.strip())


DARK_APP_CSS = """
:root {
  --ink:#e6edf7; --muted:#a0aec0; --faint:#8290a8;
  --blue:#9dadff; --blue-2:#b1bdff; --violet:#c4a7ff; --teal:#5bd6dc;
  --green:#4bd2a2; --coral:#ff827a; --amber:#f6c66b;
  --glass:rgba(20,31,49,.84); --glass-strong:rgba(25,38,59,.96); --glass-soft:rgba(19,30,47,.72);
  --glass-border:rgba(148,163,184,.20); --line:rgba(226,232,240,.11);
  --shadow:0 14px 38px -18px rgba(0,0,0,.72), 0 2px 8px rgba(0,0,0,.24);
  --shadow-sm:0 6px 18px -10px rgba(0,0,0,.6);
}
[data-testid="stAppViewContainer"] { color:var(--ink); background:linear-gradient(180deg,#0b1220 0%,#0e1726 100%); }
[data-testid="stAppViewContainer"]::before { opacity:.52; background:radial-gradient(520px 420px at 4% 0%,rgba(79,104,222,.24),transparent 70%),radial-gradient(460px 400px at 98% 8%,rgba(133,101,216,.18),transparent 70%),radial-gradient(520px 440px at 76% 100%,rgba(7,137,155,.12),transparent 70%); }
[data-testid="stSidebar"] > div:first-child { background:rgba(15,24,39,.94); border-right-color:var(--glass-border); box-shadow:8px 0 40px -24px rgba(0,0,0,.62); }
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, [data-testid="stDateInput"] > div > div, [data-testid="stChatInput"] { color:var(--ink)!important; background:#172338!important; border-color:rgba(148,163,184,.28)!important; }
input, textarea { color:var(--ink)!important; }
input::placeholder, textarea::placeholder { color:#8290a8!important; }
[role="listbox"], [role="option"], [data-baseweb="popover"] > div { color:var(--ink); background:#172338; }
[data-testid="stFileUploaderDropzone"] { background:#172338; border-color:rgba(157,173,255,.48); }
[role="tab"]:hover { background:rgba(226,232,240,.08); }
[data-testid="stAlert"] { background:var(--glass); }
[data-testid="stDataFrame"], [data-testid="stDataEditor"] { background:var(--glass-strong); }
button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stDownloadButton"] button { background:#1b2940; border-color:var(--glass-border); color:var(--ink); }
button[data-testid="stBaseButton-secondary"]:hover, [data-testid="stDownloadButton"] button:hover { border-color:var(--blue); color:var(--blue); }
[data-testid="stMetricDelta"] { color:var(--muted)!important; }
"""


def inject_app(mode="Light"):
    """Inject the selected workspace palette. Styling only; it never touches data."""
    c = app_css()
    if c:
        if mode == "Dark":
            c += DARK_APP_CSS
        st.markdown(f"<style>{c}</style>", unsafe_allow_html=True)


def user_chip_html(email: str) -> str:
    """Avatar initial + email for the sidebar. The email is escaped: it is user input rendered as HTML."""
    import html as _html
    e = _html.escape(str(email or ""), quote=True)
    initial = _html.escape((str(email or "?").strip()[:1] or "?").upper())
    return (f'<div class="fa-user"><span class="fa-avatar">{initial}</span>'
            f'<span class="fa-user-meta"><small>Signed in</small><b title="{e}">{e}</b></span></div>')


def page_header_html(eyebrow: str, title: str, sub: str = "") -> str:
    import html as _html
    s = f"<p>{_html.escape(sub)}</p>" if sub else ""
    return (f'<div class="fa-page-head"><small>{_html.escape(eyebrow)}</small><h1>{_html.escape(title)}</h1>{s}</div>')
