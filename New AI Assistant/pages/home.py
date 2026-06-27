# pages/home.py
import streamlit as st
import plotly.graph_objects as go
from theme import inject_theme
from services.supabase_service import (
    get_file_count,
    get_chunk_count,
    get_query_count,
    get_storage_bytes,
    get_storage_label,
    get_recent_queries,
    get_language_breakdown,
    get_file_type_breakdown
)

def render_hero(client):
    db_color = '#00f0ff' if client else '#f59e0b'
    db_label = 'Supabase' if client else 'SQLite'
    st.markdown(f'''
    <div style="display:flex; justify-content:space-between;
        align-items:center; padding:14px 22px;
        background:rgba(10,20,45,0.8);
        border:1px solid rgba(0,240,255,0.2);
        border-radius:12px; margin-bottom:24px;">
      <div style="font-family:'Orbitron',sans-serif;
          font-size:1.2rem; color:#e8f4ff; font-weight:700;">
          ⧡ AI Engineer Assistant</div>
      <div style="display:flex; align-items:center; gap:8px;">
        <div style="width:8px;height:8px;border-radius:50%;
            background:{db_color};"></div>
        <span style="color:{db_color}; font-size:0.8rem;
            font-weight:600;">{db_label}</span>
      </div>
    </div>''', unsafe_allow_html=True)

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

def render_activity_row(client):
    col_log, col_chart = st.columns([1.3, 0.7], gap='large')
 
    with col_log:
        st.markdown('#### 🕒  Recent Queries')
        queries = get_recent_queries(client, n=5)
        if not queries:
            st.info('No query history found.')
        else:
            for q in queries:
                q_time = q.get('created_at', '')[:10]
                st.markdown(f'''
                <div style="padding:10px 14px;
                    border-left:2px solid #00f0ff;
                    background:rgba(0,240,255,0.04);
                    border-radius:0 8px 8px 0; margin-bottom:8px;">
                  <div style="color:#e8f4ff; font-size:0.84rem;">
                      {q['question'][:72]}...</div>
                  <div style="color:#7ea8c9; font-size:0.7rem;
                      margin-top:3px;">{q_time}</div>
                </div>''', unsafe_allow_html=True)
 
    with col_chart:
        st.markdown('#### 📊  Languages Indexed')
        data = get_language_breakdown(client)
        if not data:
            st.caption("No files indexed.")
        else:
            fig = go.Figure(go.Bar(
                x=list(data.values()), y=list(data.keys()),
                orientation='h', marker_color='#00f0ff'))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#7ea8c9', height=220,
                margin=dict(l=80,r=10,t=10,b=10),
                xaxis=dict(gridcolor='rgba(255,255,255,0.03)'),
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

def render_bottom_row(client):
    col_donut, col_actions = st.columns([1, 1], gap='large')
 
    with col_donut:
        st.markdown('#### 📈  File Types')
        data = get_file_type_breakdown(client)
        if not data:
            st.caption("No codebase context indexed.")
        else:
            fig = go.Figure(go.Pie(
                labels=list(data.keys()), values=list(data.values()),
                hole=0.6,
                marker_colors=['#00f0ff','#d946ef','#7c3aed']))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                showlegend=True, height=200,
                font_color='#7ea8c9',
                margin=dict(l=10,r=10,t=10,b=10))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
 
    with col_actions:
        st.markdown('#### ⚡  Quick Actions')
        
        # Navigation helper via sidebar radio state sync
        def go_to(radio_key):
            st.session_state.nav_radio = radio_key
            st.rerun()

        if st.button('🖥  Open Swarm Console', use_container_width=True):
            go_to('🖥  Console')
        if st.button('📂  Ingest Files', use_container_width=True):
            go_to('📂  Data')
        if st.button('🗂  Query History', use_container_width=True):
            go_to('🗂  Destinations')

def render(client):
    inject_theme()
    render_hero(client)
    render_kpi_row(client)
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    render_activity_row(client)
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    render_bottom_row(client)
