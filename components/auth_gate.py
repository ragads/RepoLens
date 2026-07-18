# components/auth_gate.py
"""Login / logout / self-registration gate.

Wraps streamlit-authenticator (cookie-based sessions) over a persistent user store
(services/auth_store — Postgres via DATABASE_URL, SQLite fallback locally). Call
require_login() at the top of app.py before the router; it st.stop()s until the
visitor is authenticated.
"""
import os
import re
import time

import streamlit as st
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.hasher import Hasher

from services import auth_store

COOKIE_NAME = "devpulse_auth"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _authenticator():
    creds = auth_store.load_credentials()
    cookie_key = os.getenv("AUTH_COOKIE_KEY", "dev-insecure-cookie-key-change-me")
    authenticator = stauth.Authenticate(
        creds,
        COOKIE_NAME,
        cookie_key,
        cookie_expiry_days=30,
        auto_hash=True,  # leaves already-bcrypt-hashed passwords untouched
    )
    return authenticator, creds


def _render_auth_screen(authenticator):
    st.markdown("<div style='height:7vh'></div>", unsafe_allow_html=True)
    left, mid, right = st.columns([1, 1.5, 1])
    with mid:
        st.markdown(
            """
            <div style="text-align:center;padding:0 0 22px;">
              <svg width="48" height="48" viewBox="0 0 32 32" fill="none"
                   xmlns="http://www.w3.org/2000/svg">
                <defs><linearGradient id="agr" x1="4" y1="2" x2="28" y2="30"
                    gradientUnits="userSpaceOnUse">
                    <stop stop-color="#818CF8"/><stop offset="1" stop-color="#4F46E5"/>
                </linearGradient></defs>
                <path d="M16 1.8 L28.3 9 L28.3 23 L16 30.2 L3.7 23 L3.7 9 Z" fill="url(#agr)"/>
                <path d="M6.5 16.5 H10 L12.3 10.5 L15.8 22 L18.6 13.5 L20.2 16.5 H25.5"
                      stroke="#fff" stroke-width="1.9"
                      stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <div style="font-size:1.4rem;font-weight:700;color:var(--text-primary);
                   letter-spacing:-0.02em;margin-top:10px;">DevPulse Architect</div>
              <div style="color:var(--text-muted);font-size:0.9rem;margin-top:3px;">
                   Sign in to analyze and audit your codebase.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="auth_card"):
            tab_login, tab_signup = st.tabs(["Log in", "Create account"])

            with tab_login:
                authenticator.login(location="main", key="login")
                if st.session_state.get("authentication_status") is False:
                    st.error("Incorrect username or password.")

            with tab_signup:
                _render_signup()


def _render_signup():
    """Custom registration form so email is optional and the layout is ours."""
    with st.form("dp_register", clear_on_submit=False, border=False):
        name = st.text_input("Name")
        username = st.text_input("Username")
        email = st.text_input("Email (optional)")
        pw = st.text_input("Password", type="password")
        pw2 = st.text_input("Repeat password", type="password")
        submitted = st.form_submit_button("Create account")

    if not submitted:
        return

    # Lowercase to match streamlit-authenticator's login, which does username.lower().
    username = (username or "").strip().lower()
    errors = []
    if not (name or "").strip():
        errors.append("Enter your name.")
    if not username:
        errors.append("Choose a username.")
    elif not re.fullmatch(r"[A-Za-z0-9_.-]{3,}", username):
        errors.append("Username needs 3+ characters (letters, numbers, _ . - only).")
    elif auth_store.user_exists(username):
        errors.append("That username is already taken.")
    if len(pw or "") < 6:
        errors.append("Password must be at least 6 characters.")
    elif pw != pw2:
        errors.append("The two passwords don't match.")
    if email.strip() and not _EMAIL_RE.match(email.strip()):
        errors.append("Enter a valid email, or leave it blank.")

    if errors:
        for e in errors:
            st.error(e)
        return

    password_hash = Hasher([pw]).generate()[0]
    if auth_store.upsert_user(username, name.strip(), email.strip(), password_hash):
        st.success("Account created. Switch to **Log in** to continue.")
    else:
        st.error("Could not create the account. Please try again.")


def _loading_screen():
    st.markdown(
        """
        <div style="text-align:center;padding:22vh 0 0;">
          <svg width="46" height="46" viewBox="0 0 32 32" fill="none"
               xmlns="http://www.w3.org/2000/svg">
            <defs><linearGradient id="lgr" x1="4" y1="2" x2="28" y2="30"
                gradientUnits="userSpaceOnUse">
                <stop stop-color="#818CF8"/><stop offset="1" stop-color="#4F46E5"/>
            </linearGradient></defs>
            <path d="M16 1.8 L28.3 9 L28.3 23 L16 30.2 L3.7 23 L3.7 9 Z" fill="url(#lgr)"/>
            <path d="M6.5 16.5 H10 L12.3 10.5 L15.8 22 L18.6 13.5 L20.2 16.5 H25.5"
                  stroke="#fff" stroke-width="1.9"
                  stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <div style="color:var(--text-muted);font-size:0.9rem;margin-top:14px;">
              Restoring your session…</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def require_login():
    """Return the authenticator when logged in; otherwise render auth screen and stop."""
    authenticator, _ = _authenticator()

    # Silently restore the session from the cookie (renders no form).
    if st.session_state.get("authentication_status") is not True:
        try:
            authenticator.login(location="unrendered", key="cookie_restore")
        except Exception:  # noqa: BLE001
            pass

    if st.session_state.get("authentication_status") is True:
        return authenticator

    # The cookie is read asynchronously, so on the first run after a refresh it may
    # not be available yet. Give it ONE grace rerun behind a loader so an already
    # logged-in user never sees the sign-in form flash on refresh.
    if not st.session_state.get("_auth_settled"):
        st.session_state["_auth_settled"] = True
        _loading_screen()
        time.sleep(0.7)
        st.rerun()

    # Genuinely signed out → show the sign-in screen.
    _render_auth_screen(authenticator)
    if st.session_state.get("authentication_status") is True:
        return authenticator

    st.stop()


def render_logout(authenticator):
    """Sidebar logout control + a greeting.

    A custom logout instead of authenticator.logout(): the library's logout races
    with the persistent cookie (which re-authenticates on the next rerun). We set
    the library's `logout` flag so its cookie check short-circuits, delete the
    cookie, clear the session keys, and rerun.
    """
    name = st.session_state.get("name") or st.session_state.get("username") or "there"
    st.markdown(
        f'<div style="color:var(--text-muted);font-size:0.78rem;padding:0 4px 6px;">'
        f"Signed in as <b style='color:var(--text-primary)'>{name}</b></div>",
        unsafe_allow_html=True,
    )
    if st.button("Log out", key="dp_logout", use_container_width=True):
        try:
            authenticator.cookie_controller.delete_cookie()
        except Exception:
            pass
        st.session_state["logout"] = True
        for k in ("authentication_status", "name", "username"):
            st.session_state[k] = None
        st.rerun()
