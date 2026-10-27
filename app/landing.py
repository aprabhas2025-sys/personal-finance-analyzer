"""Signed-out experience: landing page, sign-in, sign-up. `require_login()` is the single gate used by app.py."""
import streamlit as st

from app import auth, theme


def _go(view: str):
    st.query_params.pop('view', None)
    st.session_state['view'] = view
    st.rerun()


def render_landing():
    theme.inject_landing()
    action = theme.hero()
    if isinstance(action, dict):
        view = action.get("action")
        action_id = action.get("actionId")
        if view in ("signin", "signup") and action_id != st.session_state.get("hero_action_id"):
            st.session_state["hero_action_id"] = action_id
            _go(view)


def _render_account(mode: str):
    with st.container(key="fa_login"):
        result = theme.login_page(mode=mode, error=st.session_state.get("account_error"))
    if not isinstance(result, dict):
        return

    action = result.get("action")
    action_id = result.get("attemptId")
    if action in ("switch", "back"):
        if not action_id or action_id == st.session_state.get("account_nav_action_id"):
            return
        st.session_state["account_nav_action_id"] = action_id
        st.session_state.pop("account_error", None)
        st.session_state.pop("account_attempt_id", None)
        if action == "switch":
            _go("signup" if result.get("mode") == "signup" else "signin")
        _go("landing")
    if action != mode:
        return

    attempt_id = action_id
    if not attempt_id or attempt_id == st.session_state.get("account_attempt_id"):
        return
    st.session_state["account_attempt_id"] = attempt_id
    if mode == "signup":
        user, error = auth.create_user(result.get("email", ""), result.get("password", ""), result.get("confirm", ""))
    else:
        user, error = auth.authenticate(result.get("email", ""), result.get("password", ""))
    if error:
        st.session_state["account_error"] = error
        st.rerun()

    st.session_state["user"] = user
    st.session_state["just_signed_in"] = True
    st.session_state.pop("view", None)
    st.session_state.pop("account_error", None)
    st.session_state.pop("account_attempt_id", None)
    st.query_params.pop("view", None)
    st.rerun()


def render_auth(mode: str):
    _render_account(mode)
def require_login() -> dict:
    """Returns the signed-in user ({'id','email'}); otherwise shows the landing/sign-in/sign-up page and stops the script."""
    user = st.session_state.get("user")
    if user:
        return user
    theme.inject()
    requested_view = st.query_params.get("view")
    view = requested_view if requested_view in ("signin", "signup") else st.session_state.get("view", "landing")
    if view in ("signin", "signup"):
        theme.inject_app()                  # Shared styles load first; login_page applies the tracked-light canvas.
        render_auth(view)
    else:
        render_landing()
    st.stop()
