# app.py
import importlib

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(
    page_title="DevPulse Architect",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# .env is the local fallback; on Render the real env vars are already present.
load_dotenv()

# Keep page-local widget values alive across navigation. Streamlit purges a
# widget-keyed session value when its page isn't rendered; re-touching these
# before the widgets are recreated preserves the theme and the ingest URL/branch
# when switching sections.
for _k in ("ui_theme", "ingest_url", "ingest_branch"):
    if _k in st.session_state:
        st.session_state[_k] = st.session_state[_k]

from components.auth_gate import render_logout, require_login  # noqa: E402
from theme import inject_theme  # noqa: E402

inject_theme(st.session_state.get("ui_theme", "auto"))

# Gate the whole app behind login / self-registration; halts here until signed in.
authenticator = require_login()


# ── Router ──────────────────────────────────────────────────────────────
# Order matters: the first entry is the landing section on a fresh session.
SECTIONS = {
    "Ingest Repository": ("pages.dashboard", "render_ingestion_section"),
    "Overview": ("pages.dashboard", "render_overview"),
    "Project Overview": ("pages.dashboard", "render_project_overview"),
    "Security Audit": ("pages.security_audit", "render_security_audit"),
    "Static Preview": ("pages.dashboard", "render_static_preview"),
    "Indexed Files": ("pages.dashboard", "render_files_table"),
    "Guide": ("pages.guide", "render_guide"),
    "Settings": ("pages.dashboard", "render_settings"),
}

ICONS = {
    "Ingest Repository": "↓",
    "Overview": "◔",
    "Project Overview": "◇",
    "Security Audit": "⛨",
    "Static Preview": "▣",
    "Indexed Files": "☰",
    "Guide": "?",
    "Settings": "⚙",
}


with st.sidebar:
    st.markdown(
        """
        <div class="dp-logo-wrap">
          <div class="dp-logo-mark">
            <svg width="30" height="30" viewBox="0 0 32 32" fill="none"
                 xmlns="http://www.w3.org/2000/svg" aria-label="DevPulse Architect">
              <defs>
                <linearGradient id="dpg" x1="4" y1="2" x2="28" y2="30"
                    gradientUnits="userSpaceOnUse">
                  <stop stop-color="#818CF8"/><stop offset="1" stop-color="#4F46E5"/>
                </linearGradient>
              </defs>
              <path d="M16 1.8 L28.3 9 L28.3 23 L16 30.2 L3.7 23 L3.7 9 Z"
                    fill="url(#dpg)"/>
              <path d="M6.5 16.5 H10 L12.3 10.5 L15.8 22 L18.6 13.5 L20.2 16.5 H25.5"
                    stroke="#fff" stroke-width="1.9"
                    stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="dp-logo-text">DevPulse Architect</div>
        </div>""",
        unsafe_allow_html=True,
    )

    choice = st.radio(
        "Navigation",
        list(SECTIONS.keys()),
        format_func=lambda s: f"{ICONS[s]}   {s}",
        label_visibility="collapsed",
    )

    with st.container(key="sidebar_foot"):
        st.markdown("<hr style='margin:16px 0 12px'>", unsafe_allow_html=True)
        render_logout(authenticator)


_module_name, _fn_name = SECTIONS[choice]
try:
    _render = getattr(importlib.import_module(_module_name), _fn_name)
    _render()
except Exception as exc:  # noqa: BLE001 - top-level UI boundary
    st.error(f"Failed to render **{choice}**: {exc}")
    st.exception(exc)

# Floating chat launcher + panel, present on every page.
from components.chat_widget import render_chat_widget  # noqa: E402

render_chat_widget()
