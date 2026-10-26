"""Signed-out experience: landing page, sign-in, sign-up. `require_login()` is the single gate used by app.py."""
import streamlit as st

from app import auth, config, theme


def _go(view: str):
    st.session_state["view"] = view
    st.rerun()


def _nav(show_auth_buttons: bool = True):
    with st.container(key="fa_nav"):
        a, b, c = st.columns([6, 1.2, 1.6], vertical_alignment="center")
        a.markdown(theme.BRAND_HTML, unsafe_allow_html=True)
        if show_auth_buttons:
            if b.button("Sign in", key="nav_signin"):
                _go("signin")
            if c.button("Get started", key="nav_signup", type="primary"):
                _go("signup")
        elif c.button("← Back", key="nav_back"):
            _go("landing")


def render_landing():
    _nav()
    theme.html(theme.HERO_HTML)
    with st.container(key="fa_cta"):
        _, x, y, _ = st.columns([2, 1.3, 1.3, 2])
        if x.button("Create free account", key="cta_signup", type="primary"):
            _go("signup")
        if y.button("Sign in", key="cta_signin"):
            _go("signin")
    theme.html(theme.FEATURES_HTML)
    theme.html(theme.STEPS_HTML)
    theme.html(theme.TRUST_HTML)
    if config.is_hosted():
        st.caption("This is a hosted demo. Please prefer the built-in sample data over a real statement.")
    theme.html(theme.FOOTER_HTML)


def render_auth(mode: str):
    signup = mode == "signup"
    _nav(show_auth_buttons=False)
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid, st.container(key="fa_auth"):
        theme.html(f'<h1 class="fa-auth-title">{"Create your <em>account</em>" if signup else "Welcome <em>back</em>"}</h1>'
                   f'<p class="fa-auth-sub">{"Your statement stays private to this account." if signup else "Sign in to open your workspace."}</p>')
        with st.form(f"auth_{mode}"):
            email = st.text_input("Email", placeholder="you@example.com", autocomplete="email")
            pw = st.text_input("Password", type="password", placeholder=f"At least {auth.MIN_PASSWORD} characters" if signup else "Your password",
                               autocomplete="new-password" if signup else "current-password")
            confirm = st.text_input("Confirm password", type="password", autocomplete="new-password") if signup else None
            go = st.form_submit_button("Create account" if signup else "Sign in", type="primary")
        if go:
            user, err = auth.create_user(email, pw, confirm) if signup else auth.authenticate(email, pw)
            if err:
                st.error(err)
            else:
                st.session_state.pop("view", None)
                st.session_state["user"] = user
                st.session_state["just_signed_in"] = True
                st.rerun()
        other = "signin" if signup else "signup"
        if st.button("Already have an account? Sign in" if signup else "New here? Create an account", key="switch_auth"):
            _go(other)


def require_login() -> dict:
    """Returns the signed-in user ({'id','email'}); otherwise shows the landing/sign-in/sign-up page and stops the script."""
    user = st.session_state.get("user")
    if user:
        return user
    theme.inject()
    view = st.session_state.get("view", "landing")
    render_landing() if view not in ("signin", "signup") else render_auth(view)
    st.stop()
