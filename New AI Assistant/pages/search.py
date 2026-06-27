# pages/search.py
import streamlit as st
from theme import inject_theme
from services.embedding_service import get_embedding
from services.supabase_service import semantic_search

def render_search_input():
    query = st.text_input(
        '🔍  Semantic Search',
        placeholder='Find code that handles authentication...',
        label_visibility='collapsed'
    )
    col_k, col_type, col_btn = st.columns([1.5, 2, 1])
    with col_k:
        top_k = st.slider('Results Limit', 3, 20, 8)
    with col_type:
        ft = st.radio('Search Target',
            ['All','source_code','api_doc','design_doc'], horizontal=True)
    with col_btn:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        search = st.button('🔍  Search', use_container_width=True)
    return query, top_k, ft if ft != 'All' else None, search

def render_results(results):
    for r in results:
        sim_pct = int(r['similarity'] * 100)
        # Ensure bounds
        sim_pct = max(0, min(100, sim_pct))
        
        st.markdown(f'''
        <div style="background:rgba(10,20,45,0.7);
            border:1px solid rgba(0,240,255,0.15);
            border-radius:10px; padding:16px 20px;
            margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between;
              margin-bottom:8px;">
            <span style="color:#00f0ff; font-weight:700;
                font-size:0.85rem;">{r['filename']}</span>
            <span style="color:#7ea8c9; font-size:0.78rem;
                background:rgba(0,240,255,0.1);
                padding:2px 8px; border-radius:12px;">
                {sim_pct}% match</span>
          </div>
          <div style="height:3px; background:#0a1628;
              border-radius:2px; margin-bottom:10px;">
            <div style="width:{sim_pct}%; height:100%;
                background:linear-gradient(90deg,#00f0ff,#d946ef);
                border-radius:2px;"></div>
          </div>
          <pre style="color:#b0cce0; font-size:0.78rem;
              font-family:'JetBrains Mono',monospace;
              white-space:pre-wrap; margin:0; background:rgba(0,0,0,0.2); padding:10px; border-radius:6px; border:1px solid rgba(255,255,255,0.02);">{r['content'][:400]}...</pre>
        </div>''', unsafe_allow_html=True)

def render(client):
    inject_theme()
    st.markdown("### 🔍  Semantic Index Explorer")
    query, top_k, ft, search = render_search_input()
    
    if search or query.strip():
        if query.strip():
            with st.spinner("Searching matching chunks..."):
                embedding = get_embedding(query)
                if embedding:
                    results = semantic_search(client, embedding, top_k=top_k, file_type=ft)
                    if not results:
                        st.warning("No matching chunk results found in database index.")
                    else:
                        st.markdown(f"##### Results ({len(results)} matches)")
                        render_results(results)
                else:
                    st.error("Failed to compute embeddings for query. Check your Gemini API Key in Settings.")
        else:
            st.warning("Please input search terms in the box first.")
    else:
        st.info("Please enter a query above and click Search.")
