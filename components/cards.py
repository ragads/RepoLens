# components/cards.py
import streamlit as st

def metric_card(icon, label, value, color='#00f0ff', delta=None):
    """Renders a modern, glassmorphic metric card with glowing top border."""
    delta_html = ''
    if delta:
        delta_html = f'<div style="color:{color};font-size:0.78rem;margin-top:4px;">{delta}</div>'
    st.markdown(f'''
    <div style="
        background:rgba(10, 20, 45, 0.75);
        border:1px solid {color}44;
        border-top:2px solid {color};
        border-radius:12px;
        padding:20px 24px;
        backdrop-filter:blur(12px);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);">
      <div style="font-size:1.4rem">{icon}</div>
      <div style="color:#7ea8c9;font-size:0.72rem;
          letter-spacing:0.08em;text-transform:uppercase;
          margin-top:8px">{label}</div>
      <div style="color:#e8f4ff;font-size:1.75rem;font-weight:700;
          margin-top:4px">{value}</div>
      {delta_html}
    </div>''', unsafe_allow_html=True)

def file_type_chip(label, color='#00f0ff'):
    """Returns HTML for a styled file type pill badge."""
    return (f'<span style="background:{color}18;color:{color};'
            f'border:1px solid {color}44;padding:2px 10px;'
            f'border-radius:20px;font-size:0.72rem;font-weight:500;">{label}</span>')

def glass_panel(content_fn, title=None, accent='#00f0ff'):
    """Wrap content in a glassmorphic panel container."""
    # Write top of container
    header = ''
    if title:
        header = f'''<div style="color:{accent};font-size:0.7rem;
            letter-spacing:0.1em;text-transform:uppercase;
            font-weight:700;margin-bottom:14px;">{title}</div>'''
            
    # For Streamlit rendering layout structure:
    # A container inside a styled glass border can be styled using streamlit containers,
    # or by injecting a wrapper. We render the header HTML first.
    if header:
        st.markdown(header, unsafe_allow_html=True)
    
    # Run the content function
    content_fn()
