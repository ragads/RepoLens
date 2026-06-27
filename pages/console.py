# pages/console.py
import streamlit as st
import time
import os
import json
from theme import inject_theme
from services.supabase_service import DatabaseManager, insert_query_log
from agent_orchestrator import AgentOrchestrator

AGENT_META = {
    'Planner':    {'color': '#00f0ff', 'icon': '🧠'},
    'CodeSearch': {'color': '#7c3aed', 'icon': '💻'},
    'DocSearch':  {'color': '#0ea5e9', 'icon': '📄'},
    'Generator':  {'color': '#d946ef', 'icon': '⚙️'},
}

def render_agent_tile(name, status, detail, elapsed_s):
    meta = AGENT_META.get(name, {'color':'#00f0ff','icon':'○'})
    c    = meta['color']
    icon = meta['icon']
    status_icon = {'done':'✅','running':'⏳','error':'❌'}.get(status,'○')
    st.markdown(f'''
    <div style="display:flex; align-items:flex-start; gap:14px;
        padding:14px 18px;
        background:rgba(10,20,45,0.65);
        border:1px solid {c}33;
        border-left:3px solid {c};
        border-radius:0 10px 10px 0; margin-bottom:10px;">
      <div style="font-size:1.2rem; padding-top:2px;">{icon}</div>
      <div style="flex:1;">
        <div style="color:{c}; font-weight:700; font-size:0.78rem;
            letter-spacing:0.08em; text-transform:uppercase;">
            {status_icon}  {name}
            <span style="color:#7ea8c9; font-weight:400;
                margin-left:10px; font-size:0.7rem;">{elapsed_s:.1f}s</span>
        </div>
        <div style="color:#b0cce0; font-size:0.82rem; margin-top:5px;
            font-family:'JetBrains Mono',monospace;">{detail}</div>
      </div>
    </div>''', unsafe_allow_html=True)

def render_answer_block(answer, retrieved_files, question, plan, trace, client):
    # File chips
    chips = ' '.join([
        f"""<span style="background:rgba(0,240,255,0.1);
            color:#00f0ff; border:1px solid rgba(0,240,255,0.3);
            padding:2px 10px; border-radius:20px;
            font-size:0.72rem;">{f}</span>"""
        for f in retrieved_files
    ])
    st.markdown(f'<div style="margin-bottom:12px">{chips}</div>',
        unsafe_allow_html=True)
    # Answer
    st.markdown(f'''
    <div style="background:#020c1b; border-left:3px solid #d946ef;
        border-radius:0 8px 8px 0; padding:18px;
        color:#b0cce0; font-size:0.88rem; line-height:1.75; margin-bottom:16px;">
    {answer}</div>''', unsafe_allow_html=True)
    
    # Save to Supabase
    insert_query_log(client, question, str(plan), retrieved_files, answer, trace=trace)

def render(client):
    inject_theme()
    
    st.markdown('### 🖥  Swarm Console')
    
    # Preset presets configuration
    st.markdown("<p style='color: #7ea8c9; font-size: 0.8rem; font-weight:600; margin-bottom:6px;'>Presetted prompts:</p>", unsafe_allow_html=True)
    preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
    with preset_col1:
        if st.button("📖  Explain Auth", key="p_explain", use_container_width=True):
            st.session_state['console_question'] = "Explain how auth_manager.py works and how it matches up with our architecture_design.md."
    with preset_col2:
        if st.button("🐛  Audit Bugs", key="p_bugs", use_container_width=True):
            st.session_state['console_question'] = "Find security vulnerabilities or logical bugs in auth_manager.py and write patches."
    with preset_col3:
        if st.button("🧪  Generate Tests", key="p_tests", use_container_width=True):
            st.session_state['console_question'] = "Generate comprehensive unit tests for auth_manager.py using pytest, including mock inputs."
    with preset_col4:
        if st.button("📝  Generate Docs", key="p_docs", use_container_width=True):
            st.session_state['console_question'] = "Generate complete and detailed API markdown documentation for auth_manager.py functions."

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Input text area
    question = st.text_area(
        'Ask the Swarm',
        height=120,
        max_chars=2000,
        placeholder='e.g. How does JWT authentication work in this codebase?',
        key='console_question'
    )
    char_count = len(question)
    st.caption(f'{char_count} / 2000 characters')

    col_run, col_clear = st.columns([4, 1])
    with col_run:
        run = st.button('▶  Run Swarm', use_container_width=True, type='primary')
    with col_clear:
        clear = st.button('✕ Clear', use_container_width=True)
        
    if clear:
        st.session_state.pop('console_question', None)
        st.rerun()

    # Verify Gemini API Key configuration
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        st.warning("⚠️ Gemini API Key is missing. Configure it in System Settings to run models.")

    # ── RUN PROCESS FLOW ──
    if run and gemini_key:
        if not question.strip():
            st.warning("Please supply a valid question or instructions.")
        else:
            # Set up streamed placeholders in order
            p_planner = st.empty()
            p_code = st.empty()
            p_doc = st.empty()
            p_gen = st.empty()
            
            with p_planner:
                render_agent_tile('Planner', 'running', 'Planner is coordinating query strategy...', 0.0)
                
            start_time = time.time()
            trace_logs = []
            
            def on_agent_step(step_name, data):
                elapsed = time.time() - start_time
                mapped_name = {
                    "Planner Agent": "Planner",
                    "Code Search Agent": "CodeSearch",
                    "Documentation Agent": "DocSearch",
                    "Answer Generator Agent": "Generator"
                }.get(step_name)
                
                if not mapped_name:
                    return
                    
                status = "done" if data["status"] == "success" else "running" if data["status"] == "running" else "error"
                
                tile_ph = {
                    "Planner": p_planner,
                    "CodeSearch": p_code,
                    "DocSearch": p_doc,
                    "Generator": p_gen
                }.get(mapped_name)
                
                if tile_ph:
                    with tile_ph:
                        render_agent_tile(mapped_name, status, data["message"], elapsed)
                        
                # Register in trace
                trace_logs.append({
                    "agent": mapped_name,
                    "status": status,
                    "elapsed_ms": int(elapsed * 1000),
                    "summary": data["message"]
                })
                
            try:
                db_mgr = DatabaseManager()
                orchestrator = AgentOrchestrator(db_mgr)
                
                # Execute swarm workflow
                result = orchestrator.run_workflow(question, on_step_callback=on_agent_step)

                # Fallback trace if orchestrator produced no step callbacks
                if not trace_logs:
                    trace_logs = [
                        {"agent": "Planner",    "status": "done", "elapsed_ms": 0, "summary": "Completed"},
                        {"agent": "CodeSearch", "status": "done", "elapsed_ms": 0, "summary": "Completed"},
                        {"agent": "DocSearch",  "status": "done", "elapsed_ms": 0, "summary": "Completed"},
                        {"agent": "Generator",  "status": "done", "elapsed_ms": 0, "summary": "Completed"},
                    ]

                st.markdown("### 🎯  Final Swarm Synthesis")
                render_answer_block(result["answer"], result["retrieved_files"], question, result["plan"], trace_logs, client)
                st.toast("Workflow complete!", icon="🚀")
            except Exception as e:
                st.error(f"Error during agent execution: {e}")
