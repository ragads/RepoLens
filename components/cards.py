# components/cards.py
"""Card primitives. All colors come from CSS custom properties defined in theme.py."""
import streamlit as st


def metric_card(icon, label, value, tone="accent", delta=None):
    """A KPI tile. `tone` is a token name: accent|critical|high|medium|low|info|success."""
    delta_html = ""
    if delta:
        delta_html = (
            f'<div style="color:var(--{tone});font-size:0.8125rem;'
            f'margin-top:2px;">{delta}</div>'
        )
    st.markdown(
        f"""
    <div class="dp-card dp-kpi">
      <div class="dp-kpi-icon"
           style="background:var(--{tone}-soft);color:var(--{tone});">{icon}</div>
      <div class="dp-overline">{label}</div>
      <div class="dp-kpi-value">{value}</div>
      {delta_html}
    </div>""",
        unsafe_allow_html=True,
    )


def file_type_chip(label):
    """Returns HTML for a neutral pill badge (inline use)."""
    return f'<span class="dp-chip">{label}</span>'


def severity_badge(level):
    """Returns HTML for a colored severity pill.

    level ∈ critical|high|medium|low|info|success
    """
    level = (level or "info").lower()
    return (
        f'<span class="dp-badge" style="background:var(--{level}-soft);'
        f'color:var(--{level});">{level.upper()}</span>'
    )


def section_header(title, subtitle=None):
    """Page title plus an optional muted subtitle."""
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f'<div class="dp-subtitle">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)


def empty_state(icon, title, desc):
    """Centered empty-state card. Render a CTA button after this call if needed."""
    st.markdown(
        f"""
    <div class="dp-empty">
      <div style="font-size:2.5rem;opacity:.45;line-height:1">{icon}</div>
      <div style="color:var(--text-primary);font-size:0.9375rem;
           font-weight:600;margin-top:12px">{title}</div>
      <div style="color:var(--text-muted);font-size:0.8125rem;margin-top:4px">{desc}</div>
    </div>""",
        unsafe_allow_html=True,
    )


def card(content_fn, title=None):
    """Render an overline title then the caller's content."""
    if title:
        st.markdown(f'<div class="dp-overline">{title}</div>', unsafe_allow_html=True)
    content_fn()
