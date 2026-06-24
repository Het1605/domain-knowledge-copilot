import streamlit as st
import api_client

def render_document_manager():
    """Renders the document management panel including uploads, status tables, and deletes."""
    corpus_id = st.session_state.active_corpus_id
    if not corpus_id:
        st.info("Please select a corpus first.")
        return
        
    # Initialize state keys for clearing file uploader and tracking status
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = "uploader_0"
    if "upload_status" not in st.session_state:
        st.session_state["upload_status"] = None

    st.markdown("### 📂 Document Manager")
    st.markdown("Upload reference files (PDF, DOCX, TXT, or MD) to index them for the Co-Pilot.")
    st.caption("⚠️ **Limits**: Maximum 15 documents per corpus | Maximum 15MB file size per document.")
    
    # Display persistent upload feedback toast if any
    if st.session_state["upload_status"]:
        status_type, status_msg = st.session_state["upload_status"]
        if status_type == "success":
            st.toast(status_msg, icon="✅")
        elif status_type == "error":
            st.toast(status_msg, icon="🚨")
        st.session_state["upload_status"] = None
        
    uploaded_file = st.file_uploader(
        "Upload reference document",
        type=["pdf", "docx", "txt", "md"],
        label_visibility="collapsed",
        key=st.session_state["uploader_key"]
    )
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        current_idx = int(st.session_state["uploader_key"].split("_")[1])
        
        # 1. Enforce file size limit on frontend
        if len(file_bytes) > 15 * 1024 * 1024:
            st.session_state["upload_status"] = ("error", f"File '{uploaded_file.name}' exceeds the 15MB limit. Please upload a smaller document.")
            st.session_state["uploader_key"] = f"uploader_{current_idx + 1}"
            st.rerun()
            
        # 2. Enforce document count limit on frontend
        existing_docs = api_client.list_documents(corpus_id)
        if existing_docs and len(existing_docs) >= 15:
            st.session_state["upload_status"] = ("error", "This corpus has reached the limit of 15 documents. Please delete unused files or create a new corpus.")
            st.session_state["uploader_key"] = f"uploader_{current_idx + 1}"
            st.rerun()
            
        with st.spinner(f"Ingesting {uploaded_file.name}..."):
            res = api_client.upload_document(
                corpus_id,
                uploaded_file.name,
                file_bytes
            )
            st.session_state["uploader_key"] = f"uploader_{current_idx + 1}"
            
            if res:
                st.session_state["upload_status"] = ("success", f"Uploaded '{uploaded_file.name}' successfully. Background task queued.")
            else:
                st.session_state["upload_status"] = ("error", f"A document with filename '{uploaded_file.name}' already exists, or the corpus is full.")
            st.rerun()
                
    st.divider()
    
    st.markdown("### Uploaded Documents")
    
    # Refresh control
    if st.button("🔄 Refresh Documents List", use_container_width=True, key="refresh_docs_list_btn"):
        st.rerun()
        
    docs = api_client.list_documents(corpus_id)
    if not docs:
        st.info("No documents uploaded to this corpus yet.")
    else:
        for doc in docs:
            status = doc["status"].lower()
            badge_text = doc["status"].upper()
            
            # Row display with details on the left and delete button on the right
            card_col, action_col = st.columns([6, 1], gap="small")
            with card_col:
                st.markdown(f"""
                <div class="doc-card" style="margin-bottom: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="color: #f3f4f6;">📄 {doc['filename']}</strong>
                            <div style="color: #9ca3af; font-size: 0.85rem; margin-top: 0.25rem;">
                                Type: {doc['file_type']} | Uploaded: {doc['created_at'][:19].replace('T', ' ')}
                            </div>
                        </div>
                        <span class="status-badge status-{status}">{badge_text}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with action_col:
                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_doc_{doc['id']}", help=f"Delete {doc['filename']}", use_container_width=True):
                    if api_client.delete_document(corpus_id, doc["id"]):
                        st.toast(f"Deleted '{doc['filename']}' successfully!", icon="🗑️")
                        st.rerun()
                    else:
                        st.toast("Failed to delete document.", icon="🚨")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
