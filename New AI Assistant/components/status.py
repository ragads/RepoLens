# components/status.py
import streamlit as st

def connection_badge(client):
    """Shows active connection status (Supabase or SQLite fallback)."""
    if client:
        st.markdown(
            '<span style="color:#00f0ff;font-size:0.8rem;font-weight:600;">'
            '● Supabase Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<span style="color:#d946ef;font-size:0.8rem;font-weight:600;">'
            '● SQLite Fallback</span>', unsafe_allow_html=True)

def skeleton(rows=3):
    """Show animated placeholder lines while data loads."""
    for _ in range(rows):
        st.markdown('''
        <div class="skeleton-row" style="
            height:40px;border-radius:8px;
            background: linear-gradient(90deg, 
                rgba(0,240,255,0.03) 25%, 
                rgba(0,240,255,0.09) 50%, 
                rgba(0,240,255,0.03) 75%);
            background-size: 200% 100%;
            animation: loading-skeleton 1.5s infinite;
            margin-bottom:8px;"></div>
            
        <style>
        @keyframes loading-skeleton {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        </style>
        ''', unsafe_allow_html=True)

loading_skeleton = skeleton

def error_boundary(func, *args, **kwargs):
    """Wraps database/network operations with try-except to show a friendly error card instead of crashing."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        st.markdown(f'''
        <div style="padding:16px; border:1px solid #ef4444; background:rgba(239,68,68,0.1); border-radius:8px; margin-bottom:16px;">
          <div style="color:#ef4444; font-weight:700; font-size:0.9rem;">⚠️ Connection Error</div>
          <div style="color:#f87171; font-size:0.8rem; margin-top:4px;">Failed to complete operations: {str(e)}</div>
        </div>''', unsafe_allow_html=True)
        return None
