"""Signed-out landing page and the single authentication gate used by app.py."""
import streamlit as st

from app import auth, config, theme


def _nav():
    """Brand and sign-in affordance on the landing page."""
    with st.container(key="fa_nav"):
        brand, _, action = st.columns([1.25, 5.65, 1.1], vertical_alignment="center")
        brand.markdown(theme.BRAND_HTML, unsafe_allow_html=True)
        if action.button("Sign in", key="landing_signin"):
            st.session_state["login_view"] = "signin"
            st.session_state.pop("login_error", None)
            st.session_state.pop("login_attempt_id", None)
            st.rerun()


def render_landing():
    _nav()
    with st.container(key="fa_hero"):
        theme.hero(hosted=config.is_hosted())


def _render_signin():
    with st.container(key="fa_login"):
        if st.button("← Back to Finora", key="login_back"):
            st.session_state["login_view"] = "landing"
            st.session_state.pop("login_error", None)
            st.session_state.pop("login_attempt_id", None)
            st.rerun()
        result = theme.login_page(error=st.session_state.get("login_error"))
    if not isinstance(result, dict):
        return
    action = result.get("action")
    if action == "back":
        st.session_state["login_view"] = "landing"
        st.session_state.pop("login_error", None)
        st.session_state.pop("login_attempt_id", None)
        st.rerun()
    if action != "signin":
        return
    attempt_id = result.get("attemptId")
    if not attempt_id or attempt_id == st.session_state.get("login_attempt_id"):
        return
    st.session_state["login_attempt_id"] = attempt_id
    email = result.get("email", "")
    password = result.get("password", "")
    user, error = auth.authenticate(email, password)
    if error:
        st.session_state["login_error"] = error
        st.rerun()
    st.session_state["user"] = user
    st.session_state["just_signed_in"] = True
    st.session_state["login_view"] = "landing"
    st.session_state.pop("login_error", None)
    st.session_state.pop("login_attempt_id", None)
    st.rerun()


def require_login() -> dict:
    """Return the signed-in user or show the landing/sign-in experience."""
    user = st.session_state.get("user")
    if user:
        return user
    theme.inject()
    if st.session_state.get("login_view") == "signin":
        _render_signin()
    else:
        render_landing()
    st.stop()
