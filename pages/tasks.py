# pages/tasks.py
import streamlit as st
import json
from theme import inject_theme
from services.supabase_service import get_recent_queries

AGENTS = [
    ('Planner',    '#00f0ff', '🧠'),
    ('CodeSearch', '#7c3aed', '💻'),
    ('DocSearch',  '#0ea5e9', '📄'),
    ('Generator',  '#d946ef', '⚙️'),
]

def render_stepper(trace: list):
    """trace = list of dicts from agent_trace JSONB column"""
    trace_map = {t['agent']: t for t in (trace or [])}
    for name, color, icon in AGENTS:
        t = trace_map.get(name)
        if t:
            status = t.get('status','done')
            elapsed = f"{t.get('elapsed_ms',0)/1000:.1f}s"
            summary = t.get('summary','Complete')
        else:
            status, elapsed, summary = 'pending', '—', 'Not yet run'
            
        opacity = '1' if status != 'pending' else '0.4'
        s_icon  = '✅' if status=='done' else '⏳' if status=='running' else '○'
        st.markdown(f'''
        <div style="display:flex; gap:14px; padding:12px 16px;
            background:rgba(10,20,45,0.65);
            border:1px solid {color}33;
            border-left:3px solid {color};
            border-radius:0 10px 10px 0;
            margin-bottom:8px; opacity:{opacity};">
          <div style="font-size:1.2rem">{icon}</div>
          <div style="flex:1">
            <div style="color:{color}; font-weight:700; font-size:0.78rem;
                text-transform:uppercase; letter-spacing:0.08em;">
                {s_icon} {name}
                <span style="color:#7ea8c9; font-weight:400;
                    margin-left:10px; font-size:0.7rem;">{elapsed}</span>
            </div>
            <div style="color:#7ea8c9; font-size:0.78rem;
                margin-top:3px;">{summary}</div>
          </div>
        </div>''', unsafe_allow_html=True)

def render(client):
    inject_theme()
    st.markdown("### ⚡  Agent Pipeline Tracer")
    
    # ── SECTION A: Query Selector ──
    queries = get_recent_queries(client, n=20)
    if not queries:
        st.info("No queries found in logs. Run some workflows in the Console page first.")
        return
        
    options = {}
    for q in queries:
        time_str = q.get('created_at', '')
        if "T" in time_str:
            time_str = time_str.split("T")[1][:5]
        else:
            time_str = time_str[11:16]
        label = f"[{time_str}] {q['question'][:65]}..."
        options[label] = q
        
    selected_label = st.selectbox('Select a Query to Trace', list(options.keys()))
    selected_query = options[selected_label]
    
    # Load trace logs
    trace = selected_query.get("agent_trace")
    if isinstance(trace, str) and trace.strip():
        try:
            trace = json.loads(trace)
        except Exception:
            trace = []
            
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # ── SECTION B: 4-Step Stepper ──
    render_stepper(trace)
    
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── SECTION C: Agent Detail Drawer ──
    st.markdown("### 📋  Agent Execution Logs")
    if not trace:
        st.caption("No detailed agent trace logs available for this query.")
    else:
        for idx, step in enumerate(trace):
            name = step.get("agent", "Agent")
            summary = step.get("summary", "")
            elapsed = f"{step.get('elapsed_ms', 0)/1000:.1f}s"
            
            with st.expander(f"Step {idx+1}: {name} ({elapsed})"):
                st.write(summary)
                
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # ── SECTION D: Retrieved Chunks Viewer ──
    st.markdown("### 📂  Consulted Codebase Contexts")
    retrieved = selected_query.get("retrieved_files")
    if isinstance(retrieved, str):
        try:
            retrieved = json.loads(retrieved)
        except Exception:
            retrieved = [retrieved]
            
    if not retrieved:
        st.caption("No codebase context files were retrieved for this query.")
    else:
        for rf in retrieved:
            st.markdown(f"- 📄 `{rf}`")
