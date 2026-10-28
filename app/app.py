"""Signed-in Streamlit gate and embedded finance dashboard."""
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import streamlit.components.v1 as components

from app import landing

st.set_page_config(page_title="Personal Finance Analyzer", page_icon="📈", layout="wide")
user = landing.require_login()  # Keep the existing 3D landing, sign-in, and sign-up flow.

if st.button("Sign out", key="finance_signout", help="Sign out of your finance workspace"):
    st.session_state.pop("user", None)
    st.session_state.pop("view", None)
    st.rerun()

assets = ROOT / "finance-ui" / "dist" / "assets"
js_files = sorted(assets.glob("index-*.js"))
css_files = sorted(assets.glob("index-*.css"))
if len(js_files) != 1 or len(css_files) != 1:
    st.error("The finance dashboard bundle is missing. Rebuild finance-ui/dist before starting the app.")
    st.stop()

js = js_files[0].read_text(encoding="utf-8").replace("</script", "<\\/script")
css = css_files[0].read_text(encoding="utf-8").replace("</style", "<\\/style")
user_id = html.escape(str(user.get("id", "local")), quote=True)
user_email = html.escape(str(user.get("email", "")), quote=True)

page = (
    "<!doctype html><html lang='en'><head><meta charset='UTF-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1.0'>"
    f"<style>{css}</style>"
    "<style>html,body,#root{margin:0;width:100%;min-height:100%;}"
    "body{min-height:100vh;overflow:auto;}"
    ".app-shell{min-height:100vh;margin:0;border:0;border-radius:0;overflow:hidden;}"
    ".topbar{padding-right:150px!important;}@media(max-width:640px){.topbar{padding-right:104px!important;}}"
    "</style></head><body>"
    f"<div id='root' data-user-id='{user_id}' data-user-email='{user_email}'></div>"
    f"<script type='module'>{js}</script></body></html>"
)

st.markdown(
    """<style>
    [data-testid="stSidebar"], [data-testid="stHeader"], footer,
    [data-testid="stDeployButton"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] { display:none !important; }
    [data-testid="stAppViewContainer"] { min-height:100vh; }
    .block-container { max-width:none !important; padding:0 !important; }
    .st-key-finance_signout { position:fixed !important; top:14px !important; right:20px !important;
      z-index:999999 !important; width:110px !important; }
    .st-key-finance_signout button { min-height:44px; border-radius:999px; padding:4px 12px;
      background:#ffffff; color:#151a23; border:1px solid #d5d9e0;
      font-size:14px; font-weight:600; }
    .st-key-finance_signout button p { font-size:14px; font-weight:600; }
    @media (max-width:640px) { .st-key-finance_signout { width:84px !important; right:12px !important; } }
    .st-key-finance_signout button:hover { border-color:#14b8a6; color:#0f766e; }
    /* The dashboard fills the window and scrolls inside itself (fixed sidebar, one scrolling content area). */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] { overflow:hidden !important; }
    iframe[title="st.iframe"] { position:fixed !important; inset:0 !important; display:block;
      width:100vw !important; height:100vh !important; height:100dvh !important; border:0; z-index:1; }
    </style>""",
    unsafe_allow_html=True,
)
components.html(page, height=980, scrolling=True)
