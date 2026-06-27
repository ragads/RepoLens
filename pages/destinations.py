# pages/destinations.py
import streamlit as st
import json
from datetime import datetime, timedelta
from theme import inject_theme
from components.status import skeleton
from services.supabase_service import (
    get_query_count,
    get_queries_today,
    get_avg_files_per_query,
    get_query_history
)

PAGE_SIZE = 10

def render_summary_strip(client):
    c1, c2, c3 = st.columns(3, gap='medium')
    with c1: 
        st.metric('Total Queries', get_query_count(client))
    with c2: 
        st.metric('Queries Today', get_queries_today(client))
    with c3: 
        st.metric('Avg Files Retrieved', get_avg_files_per_query(client))

def render_query_cards(client, search_term, date_filter):
    # Fetch a set of queries for filtering
    raw_queries = get_query_history(client, limit=200, offset=0)
    
    # Apply search filter
    filtered = raw_queries
    if search_term.strip():
        q_term = search_term.lower()
        filtered = [
            q for q in filtered
            if q_term in q.get('question', '').lower() or q_term in q.get('answer', '').lower()
        ]
        
    # Safe timestamp parser handles both SQLite and Supabase formats
    def safe_parse_dt(ts_str):
        try:
            ts = ts_str.replace('Z', '').replace('+00:00', '').replace('T', ' ').split('.')[0]
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.min

    # Apply date filter
    now = datetime.utcnow()
    if date_filter == 'Today':
        today_str = now.strftime('%Y-%m-%d')
        filtered = [q for q in filtered if q.get('created_at', '')[:10] == today_str]
    elif date_filter == 'Last 7 Days':
        cutoff = now - timedelta(days=7)
        filtered = [q for q in filtered if safe_parse_dt(q.get('created_at', '')) >= cutoff]
    elif date_filter == 'Last 30 Days':
        cutoff = now - timedelta(days=30)
        filtered = [q for q in filtered if safe_parse_dt(q.get('created_at', '')) >= cutoff]

    total = len(filtered)
    if not filtered:
        st.info('No matching query logs found.')
        return

    # Pagination state
    if 'hist_page' not in st.session_state:
        st.session_state.hist_page = 0
        
    page = st.session_state.hist_page
    max_pages = max(0, (total - 1) // PAGE_SIZE)
    if page > max_pages:
        page = max_pages
        st.session_state.hist_page = page

    # Slice page items
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_queries = filtered[start_idx:end_idx]

    # Render cards
    for q in page_queries:
        with st.expander(f"🔍  {q['question'][:80]}"):
            # retrieved files
            files = q.get('retrieved_files', '[]')
            try:
                files_list = json.loads(files) if isinstance(files, str) else files
            except Exception:
                files_list = [files]
                
            chips = ' '.join([
                f'<code style="background:rgba(0,240,255,0.08);'
                f'color:#00f0ff;padding:1px 7px;'
                f'border-radius:4px;margin-right:6px;display:inline-block;">{f}</code>'
                for f in files_list
            ])
            if chips:
                st.markdown(chips, unsafe_allow_html=True)
                
            st.markdown(f'''
            <div style="background:#020c1b; border-left:3px solid #d946ef;
                padding:14px; border-radius:0 8px 8px 0;
                color:#b0cce0; font-size:0.85rem;
                line-height:1.7; margin-top:10px; margin-bottom:10px;">
            {q['answer']}
            </div>''', unsafe_allow_html=True)
            st.caption(f"Executed at: {q.get('created_at', '')}")

    # Pagination controls
    cp, ci, cn = st.columns([1, 3, 1])
    if page > 0 and cp.button('← Prev'):
        st.session_state.hist_page = page - 1
        st.rerun()
        
    ci.markdown(f"<div style='text-align:center; color:#7ea8c9; font-size:0.8rem; margin-top:6px;'>Page {page+1} of {max_pages+1}  ({total} matches)</div>", unsafe_allow_html=True)
    
    if (page+1)*PAGE_SIZE < total and cn.button('Next →'):
        st.session_state.hist_page = page + 1
        st.rerun()

def render(client):
    inject_theme()
    st.markdown("### 🗂  Query History Destinations")
    render_summary_strip(client)
    
    st.markdown("<hr style='border-color:rgba(0,240,255,0.15); margin:20px 0;'>", unsafe_allow_html=True)
    
    # Filter controls
    col_search, col_date = st.columns([3, 1])
    with col_search:
        search_query = st.text_input('Search', placeholder='Search past queries or answers...', label_visibility='collapsed')
    with col_date:
        date_filter = st.selectbox(
            'Date Filter', 
            ['All Time', 'Today', 'Last 7 Days', 'Last 30 Days'], 
            label_visibility='collapsed'
        )
        
    render_query_cards(client, search_query, date_filter)
