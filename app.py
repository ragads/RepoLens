# app.py
import streamlit as st
import importlib
from theme import inject_theme

st.set_page_config(
    page_title='DevPulse Architect',
    page_icon='⧡',
    layout='wide',
    initial_sidebar_state='expanded'
)

inject_theme()

with st.sidebar:
    # Logo — NO subtitle
    st.markdown('''
    <div style="padding:24px 20px 12px; text-align:center;">
      <div style="font-family:'Orbitron',sans-serif;
          font-size:1.1rem; color:#00f0ff;
          letter-spacing:0.1em; font-weight:700;">⧡ DevPulse Architect</div>
    </div>''', unsafe_allow_html=True)

    st.markdown('<hr style="border-color:rgba(0,240,255,0.15);margin:0 0 12px">',
        unsafe_allow_html=True)

    # Static Navigation Label (No blue dot, no folder icon)
    st.markdown('''
    <div style="background:rgba(0,240,255,0.06); 
        border-left:3px solid #00f0ff; 
        padding:10px 20px; 
        margin:0 8px;
        border-radius:4px;
        color:#e0f7fc;
        font-weight:600;
        font-size:0.95rem;
        letter-spacing:0.05em;
        font-family:'Space Grotesk', sans-serif;">Dashboard</div>
    ''', unsafe_allow_html=True)

# Route directly to dashboard page
mod = importlib.import_module('pages.dashboard')
mod.render()
