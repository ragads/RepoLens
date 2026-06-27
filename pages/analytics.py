# pages/analytics.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from theme import inject_theme
from services.supabase_service import (
    get_file_count,
    get_chunk_count,
    get_query_count,
    get_storage_label,
    get_queries_per_day,
    get_top_retrieved_files,
    get_files_per_day,
    get_language_breakdown
)

def render_kpi_row(client):
    c1, c2, c3, c4 = st.columns(4, gap='medium')
    kpis = [
        (c1, '📂', 'Indexed Files',  str(get_file_count(client)),   '#00f0ff'),
        (c2, '🧩', 'Total Chunks',   str(get_chunk_count(client)),  '#7c3aed'),
        (c3, '🔍', 'Queries Run',    str(get_query_count(client)),  '#0ea5e9'),
        (c4, '💾', 'Storage Used',   get_storage_label(client),     '#d946ef'),
    ]
    for col, icon, label, value, color in kpis:
        with col:
            st.markdown(f'''
            <div style="background:rgba(10,20,45,0.75);
                border:1px solid {color}44; border-top:2px solid {color};
                border-radius:12px; padding:20px 22px;
                backdrop-filter:blur(10px);">
              <div style="font-size:1.4rem">{icon}</div>
              <div style="color:#7ea8c9; font-size:0.7rem;
                  letter-spacing:0.08em; text-transform:uppercase;
                  margin-top:8px">{label}</div>
              <div style="color:#e8f4ff; font-size:1.7rem;
                  font-weight:700; margin-top:4px">{value}</div>
            </div>''', unsafe_allow_html=True)

def render_queries_chart(client):
    st.markdown('#### 📈  Queries Per Day (Last 30 Days)')
    data = get_queries_per_day(client, days=30)
    if not data:
        st.info("No queries recorded.")
        return
        
    days   = [r['day'] for r in data]
    counts = [r['count'] for r in data]
    
    fig = go.Figure(go.Scatter(
        x=days, y=counts, fill='tozeroy',
        line=dict(color='#00f0ff', width=2.5),
        fillcolor='rgba(0,240,255,0.08)',
        marker=dict(size=4)
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#7ea8c9',
        font_family='Space Grotesk',
        height=240,
        margin=dict(l=40, r=20, t=10, b=20),
        xaxis=dict(gridcolor='rgba(255,255,255,0.03)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.03)')
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_top_files_chart(client):
    st.markdown('#### 🏆  Top Retrieved Files')
    data = get_top_retrieved_files(client, limit=10)
    if not data:
        st.info("No file retrieval hits recorded.")
        return
        
    df = pd.DataFrame(data)
    fig = go.Figure(go.Bar(
        x=df["count"], y=df["filename"],
        orientation='h',
        marker=dict(
            color='rgba(124, 58, 237, 0.65)',
            line=dict(color='#7c3aed', width=1.5)
        )
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#7ea8c9',
        font_family='Space Grotesk',
        height=280,
        margin=dict(l=140, r=10, t=10, b=20),
        xaxis=dict(gridcolor='rgba(255,255,255,0.03)'),
        yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_indexing_timeline(client):
    st.markdown('#### 📅  Files Ingested Timeline')
    data = get_files_per_day(client, days=30)
    if not data:
        st.info("No indexing data recorded.")
        return
        
    df = pd.DataFrame(data).sort_values(by="day")
    fig = go.Figure(go.Scatter(
        x=df["day"], y=df["count"], fill='tozeroy',
        line=dict(color='#d946ef', width=2.5),
        fillcolor='rgba(217, 70, 239, 0.08)',
        marker=dict(size=4)
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#7ea8c9',
        font_family='Space Grotesk',
        height=240,
        margin=dict(l=40, r=20, t=10, b=20),
        xaxis=dict(gridcolor='rgba(255,255,255,0.03)'),
        yaxis=dict(gridcolor='rgba(255,255,255,0.03)')
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_language_chart(client):
    st.markdown('#### 📊  Indexed Languages')
    data = get_language_breakdown(client)
    if not data:
        st.info("No files indexed.")
        return
        
    fig = go.Figure(go.Bar(
        x=list(data.values()), y=list(data.keys()),
        orientation='h', marker_color='#0ea5e9'))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#7ea8c9',
        font_family='Space Grotesk',
        height=280,
        margin=dict(l=80, r=10, t=10, b=20),
        xaxis=dict(gridcolor='rgba(255,255,255,0.03)'),
        yaxis=dict(autorange="reversed")
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render(client):
    inject_theme()
    st.markdown("### 📊  System Usage Analytics")
    render_kpi_row(client)
    
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns(2, gap='large')
    with col_l:
        render_queries_chart(client)
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        render_indexing_timeline(client)
        
    with col_r:
        render_top_files_chart(client)
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        render_language_chart(client)
