"""Visual theme: injects app/style.css and renders the hero banner. Styling only; it never touches data and never breaks the app."""
from pathlib import Path

import streamlit as st

CSS_PATH = Path(__file__).with_name("style.css")

HERO_HTML = (
    '<div class="fa-hero"><div class="fa-hero-inner">'
    '<div class="fa-hero-copy">'
    '<span class="fa-eyebrow"><i></i>Personal Finance Analyzer</span>'
    '<h1>Know exactly where your money <em>goes</em></h1>'
    '<p>Upload a bank or UPI statement and get clean categories, unusual-charge alerts, subscriptions, budgets and a next-month forecast.</p>'
    '</div>'
    '<div class="fa-hero-card"><small>What you get</small>'
    '<div>Auto-categorised spending</div><div>Duplicate &amp; unusual charge alerts</div><div>Subscriptions and recurring bills</div>'
    '<div>Budgets with early warnings</div><div>Next-month forecast</div><div>Ask questions in plain English</div>'
    '</div></div></div>'
)


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


def hero():
    st.markdown(HERO_HTML, unsafe_allow_html=True)
