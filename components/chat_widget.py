# components/chat_widget.py
import streamlit as st
import services.chat_service as chat_service
import services.database_service as database_service

def render_chat_widget():
    """Renders the AI Codebase Chat as a medium-sized floating popover in the bottom-right corner."""
    
    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Sanitize chat history to only contain strings (fixes previous delta generator issues)
    st.session_state["chat_history"] = [
        m for m in st.session_state["chat_history"]
        if isinstance(m, dict)
        and isinstance(m.get("role"), str)
        and isinstance(m.get("content"), str)
    ]

    # Inject CSS to make the popover look like a floating chat widget
    st.markdown(
        """
        <style>
        /* Float the popover wrapper in the bottom-right corner */
        div[data-testid="stPopover"] {
            position: fixed !important;
            bottom: 25px !important;
            right: 25px !important;
            z-index: 999999 !important;
        }

        /* Style the trigger button as a circular FAB */
        div[data-testid="stPopover"] > button {
            border-radius: 50% !important;
            width: 65px !important;
            height: 65px !important;
            font-size: 32px !important;
            background-color: #6366f1 !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        }

        div[data-testid="stPopover"] > button:hover {
            transform: scale(1.1) rotate(5deg) !important;
            background-color: #4f46e5 !important;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* Hide the caret/down-arrow inside the popover button */
        div[data-testid="stPopover"] > button span[data-testid="stIcon"] {
            display: none !important;
        }

        /* Removed stPopoverBody override to avoid blank rendering bug */

        .floating-chat-header {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding-bottom: 10px !important;
            border-bottom: 1px solid var(--border, #e2e8f0) !important;
            margin-bottom: 10px !important;
        }

        @media (prefers-color-scheme: dark) {
            .floating-chat-header {
                border-bottom-color: #2d2d44 !important;
            }
        }

        .floating-chat-title {
            font-weight: 700 !important;
            font-size: 1.15rem !important;
            color: var(--text-primary) !important;
        }
        
        .floating-chat-subtitle {
            font-size: 0.75rem !important;
            color: var(--text-muted, #718096) !important;
        }

        .chat-scroll-area {
            height: 380px !important;
            overflow-y: auto !important;
            margin-bottom: 10px !important;
            padding-right: 5px !important;
        }
        
        /* Ensure the input form stays at the bottom */
        div[data-testid="stForm"] {
            margin-top: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Render popover
    with st.popover("💬"):
        # Header
        st.markdown(
            """
            <div class="floating-chat-header">
                <div>
                    <div class="floating-chat-title">AI Codebase Assistant</div>
                    <div class="floating-chat-subtitle">Grounded in your repository index</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Messages area
        st.markdown('<div class="chat-scroll-area">', unsafe_allow_html=True)
        
        if not st.session_state["chat_history"]:
            st.caption("Ask questions about the repository files, libraries, or architecture.")
            
            st.markdown("**Suggested Questions:**")
            sugs = [
                "Explain the project architecture",
                "What languages are used in this codebase?",
                "Can you summarize the main components?"
            ]
            for idx, sug in enumerate(sugs):
                if st.button(sug, key=f"sug_popover_{idx}", use_container_width=True):
                    st.session_state["chat_history"].append({"role": "user", "content": sug})
                    st.rerun()
        else:
            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # If last message is from user, generate response
            if st.session_state["chat_history"][-1]["role"] == "user":
                user_prompt = st.session_state["chat_history"][-1]["content"]
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing codebase..."):
                        try:
                            response = chat_service.ask_question(user_prompt)
                            if not isinstance(response, str):
                                response = str(response)
                        except Exception as e:
                            response = f"Failed to get response: {e}"
                        st.markdown(response)
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Input Form
        with st.form("chat_popover_form", clear_on_submit=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                user_query = st.text_input("Message...", placeholder="Type a message...", label_visibility="collapsed")
            with c2:
                submit_button = st.form_submit_button("Send", use_container_width=True)
            
            if submit_button and user_query.strip():
                st.session_state["chat_history"].append({"role": "user", "content": user_query.strip()})
                st.rerun()

        # Clear Chat Button
        if st.session_state["chat_history"]:
            if st.button("Clear Chat", key="clear_chat_popover_btn", use_container_width=True):
                st.session_state["chat_history"] = []
                st.rerun()
