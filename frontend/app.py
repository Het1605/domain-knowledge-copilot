import sys
import os
import streamlit as st
import importlib

# Setup path to import api_client and view packages reliably
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Prevent caching issues by reloading modules on each rerun
import api_client
importlib.reload(api_client)

from views import auth, sidebar, chat, documents
importlib.reload(auth)
importlib.reload(sidebar)
importlib.reload(chat)
importlib.reload(documents)

# Initialize page settings
st.set_page_config(
    page_title="Domain Knowledge Co-Pilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium dark CSS styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Custom indicator highlights on active Segmented Control (Tabs) */
div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
    background: linear-gradient(135deg, #a855f7 0%, #3b82f6 100%) !important;
    color: #ffffff !important;
    border: none !important;
}



/* Gradient Header */
.gradient-text {
    background: linear-gradient(135deg, #a855f7 0%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    text-align: center;
}

.sub-text {
    color: #9ca3af;
    font-size: 1rem;
    margin-bottom: 2rem;
    text-align: center;
}

/* Document cards (slightly lighter container backdrops for card depth) */
.doc-card {
    background-color: #131a26;
    border: 1px solid #222d3d;
    border-radius: 8px;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    transition: transform 0.2s, border-color 0.2s;
}
.doc-card:hover {
    transform: translateY(-1px);
    border-color: #3b82f6;
}

/* Status Badges */
.status-badge {
    padding: 0.15rem 0.5rem;
    border-radius: 9999px;
    font-size: 0.7rem;
    font-weight: 600;
    text-align: center;
    display: inline-block;
}
.status-ingesting {
    background-color: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
}
.status-completed {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
}
.status-failed {
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

/* Citation card */
.citation-block {
    background-color: #0d121c;
    border-left: 3px solid #3b82f6;
    padding: 0.75rem 1rem;
    margin-bottom: 0.75rem;
    border-radius: 0 6px 6px 0;
}

/* Hide Streamlit header completely to maximize screen space and prevent overlapping click-blocking */
header[data-testid="stHeader"], header {
    display: none !important;
}

/* Disable main scrollbars globally */
html, body, [data-testid="stAppViewContainer"], section[data-testid="stMain"], section.main, .stApp {
    overflow: hidden !important;
    height: 100vh !important;
    max-height: 100vh !important;
}

/* Ensure the main block container fills the space and doesn't scroll */
div[data-testid="stAppViewBlockContainer"], div.block-container {
    height: 100vh !important;
    max-height: 100vh !important;
    padding-top: 0.5rem !important; /* Lifts the content to the very top */
    padding-bottom: 0.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# State Initializations
if "token" not in st.session_state:
    st.session_state["token"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "active_corpus_id" not in st.session_state:
    st.session_state["active_corpus_id"] = None
if "active_session_id" not in st.session_state:
    st.session_state["active_session_id"] = None

# Routing Handler
if st.session_state["token"] is None:
    auth.render_auth_portal()
else:
    # Sidebar rendering (contains corpus selection and management options)
    selected_corpus = sidebar.render_sidebar()
    
    # Main Workspace content rendering
    if st.session_state.active_corpus_id is None:
        st.markdown("<h1 class='gradient-text' style='margin-top: 5rem;'>Domain Knowledge Co-Pilot</h1>", unsafe_allow_html=True)
        st.markdown("<p class='sub-text'>Please create or select a Document Corpus in the sidebar to begin.</p>", unsafe_allow_html=True)
    else:
        # Render horizontal navigation segmented control
        active_tab = st.segmented_control(
            "Navigation",
            options=["💬 Chat Co-Pilot", "📂 Document Manager"],
            default="💬 Chat Co-Pilot",
            label_visibility="collapsed"
        )
        
        # Add a subtle margin below the navigation control
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        if active_tab == "💬 Chat Co-Pilot":
            st.markdown("""
            <style>
            /* Make chat messages responsive within viewport and prevent overlap with bottom input */
            .st-key-chat_messages_container {
                height: 62vh !important;
                max-height: 62vh !important;
                overflow-y: auto !important;
                padding-bottom: 20px !important;
            }
            </style>
            """, unsafe_allow_html=True)
            chat.render_chat_view(selected_corpus)
        elif active_tab == "📂 Document Manager":
            st.markdown("""
            <style>
            /* Make document list container responsive within viewport */
            .st-key-documents_list_container {
                height: 52vh !important;
                max-height: 52vh !important;
                overflow-y: auto !important;
            }
            </style>
            """, unsafe_allow_html=True)
            documents.render_document_manager()
