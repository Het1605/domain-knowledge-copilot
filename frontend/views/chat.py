import streamlit as st
import api_client
import json
import logging

logger = logging.getLogger(__name__)

def render_chat_view(selected_corpus):
    """Renders the full-screen centered chat view for RAG Q&A (ChatGPT UI Style)."""
    # Automated Chat Session Lookup/Creation per Corpus
    corpus_id = st.session_state.active_corpus_id
    sessions = api_client.list_chat_sessions(corpus_id)
    if not sessions:
        # Create a default session under the hood
        created_sess = api_client.create_chat_session(corpus_id, "Default Chat")
        if created_sess:
            st.session_state.active_session_id = created_sess["id"]
        else:
            st.session_state.active_session_id = None
    else:
        # Match to the active session index
        st.session_state.active_session_id = sessions[0]["id"]

    if st.session_state.active_session_id is None:
        st.info("Initializing chat session context. Please wait...")
    else:
        session_id = st.session_state.active_session_id
        
        # Fetch message history logs
        messages = api_client.list_messages(session_id)
        
        # Display messages inside a scrollable container (ChatGPT UI Style)
        with st.container(height=550, border=False):
            for msg in messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
                    # Render citations if assistant message
                    citations_json = msg.get("citations_json")
                    if citations_json:
                        try:
                            citations = json.loads(citations_json)
                            if citations:
                                with st.expander("📚 View Citations"):
                                    for idx, citation in enumerate(citations, 1):
                                        page_lbl = f", Page {citation['page_number']}" if citation.get("page_number") is not None and citation["page_number"] != -1 else ""
                                        st.markdown(f"""
                                        <div class="citation-block">
                                            <strong>[{idx}] {citation['filename']}{page_lbl}</strong><br/>
                                            <span style="color: #9ca3af; font-size: 0.9rem;">"{citation['text']}"</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                        except Exception as e:
                            logger.error(f"Error parsing citation JSON: {e}")

        # Chat input pins to bottom automatically
        user_prompt = st.chat_input("Ask a question about your documents...")
        if user_prompt:
            with st.chat_message("user"):
                st.markdown(user_prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Analyzing document context..."):
                    response = api_client.send_message(session_id, user_prompt)
                    if response:
                        st.markdown(response["content"])
                        citations = response.get("citations", [])
                        if citations:
                            with st.expander("📚 View Citations"):
                                for idx, citation in enumerate(citations, 1):
                                    page_lbl = f", Page {citation['page_number']}" if citation.get("page_number") is not None and citation["page_number"] != -1 else ""
                                    st.markdown(f"""
                                    <div class="citation-block">
                                        <strong>[{idx}] {citation['filename']}{page_lbl}</strong><br/>
                                        <span style="color: #9ca3af; font-size: 0.9rem;">"{citation['text']}"</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                        st.rerun()
