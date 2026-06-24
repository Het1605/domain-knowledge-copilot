import streamlit as st
import api_client

def render_sidebar() -> dict | None:
    """Renders all sidebar elements including user profiles, corpora CRUD, and document uploads."""
    selected_corpus = None
    with st.sidebar:
        st.markdown(f"### 👤 Welcome, **{st.session_state.username}**")
        if st.button("Log Out", use_container_width=True):
            st.session_state["token"] = None
            st.session_state["username"] = None
            st.session_state["active_corpus_id"] = None
            st.session_state["active_session_id"] = None
            st.rerun()
            
        st.divider()
        
        # CORPUS CRUD MANAGEMENT
        st.markdown("### 📚 Select Corpus")
        corpora = api_client.list_corpora()
        corpus_names = [c["name"] for c in corpora]
        
        if corpus_names:
            # Sync active index
            active_index = 0
            if st.session_state.active_corpus_id:
                for idx, c in enumerate(corpora):
                    if c["id"] == st.session_state.active_corpus_id:
                        active_index = idx
                        break
            
            selected_name = st.selectbox(
                "Select Corpus",
                options=corpus_names,
                index=active_index,
                label_visibility="collapsed"
            )
            
            selected_corpus = next(c for c in corpora if c["name"] == selected_name)
            
            # If the selected corpus changed, reset chat session
            if st.session_state.active_corpus_id != selected_corpus["id"]:
                st.session_state.active_corpus_id = selected_corpus["id"]
                st.session_state.active_session_id = None
                st.rerun()
        else:
            st.info("Create a new corpus to begin.")
            st.session_state.active_corpus_id = None
            st.session_state.active_session_id = None
            
        # Add new corpus
        with st.expander("➕ Create Corpus"):
            new_corpus_name = st.text_input("Corpus Name", key="create_corpus_name")
            if st.button("Create", key="create_corpus_button", use_container_width=True):
                if new_corpus_name.strip():
                    created = api_client.create_corpus(new_corpus_name.strip())
                    if created:
                        st.session_state.active_corpus_id = created["id"]
                        st.session_state.active_session_id = None
                        st.success(f"Created '{new_corpus_name}'")
                        st.rerun()
                else:
                    st.error("Name cannot be empty.")
                    
        # Delete active corpus
        if st.session_state.active_corpus_id:
            if st.button("🗑️ Delete Selected Corpus", use_container_width=True, type="secondary"):
                if api_client.delete_corpus(st.session_state.active_corpus_id):
                    st.session_state.active_corpus_id = None
                    st.session_state.active_session_id = None
                    st.success("Corpus deleted.")
                    st.rerun()
                    
    return selected_corpus
