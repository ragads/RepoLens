# components/status.py
"""Status / feedback primitives. Colors come from theme.py CSS variables."""
import streamlit as st


def connection_badge(label="Local SQLite"):
    """Small status dot + label, for the sidebar footer."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;">'
        f'<span style="width:6px;height:6px;border-radius:50%;'
        f'background:var(--success);display:inline-block;"></span>'
        f'<span style="color:var(--text-muted);font-size:0.75rem;">{label}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def skeleton(rows=3):
    """Placeholder rows while data loads."""
    for _ in range(rows):
        st.markdown(
            '<div style="height:40px;border-radius:var(--radius-md);'
            'background:var(--surface-2);margin-bottom:8px;"></div>',
            unsafe_allow_html=True,
        )


loading_skeleton = skeleton


def error_boundary(func, *args, **kwargs):
    """Run `func`, showing a friendly error card instead of crashing the page."""
    try:
        return func(*args, **kwargs)
    except Exception as e:  # noqa: BLE001 - deliberate catch-all for the UI boundary
        st.error(f"Operation failed: {e}")
        return None
