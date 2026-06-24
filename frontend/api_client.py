import os
import requests
import streamlit as st
import logging

logger = logging.getLogger(__name__)

# Base API URL configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

def get_headers() -> dict:
    """Retrieves authentication headers utilizing token saved in Streamlit session state."""
    headers = {}
    token = st.session_state.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

# ==============================================================================
# AUTHENTICATION HANDLERS
# ==============================================================================
def signup(username: str, password: str) -> tuple[bool, str]:
    """Submits account registration to the backend."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/register",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 201:
            return True, "User registered successfully! Please login."
        else:
            detail = response.json().get("detail", "Signup failed.")
            return False, detail
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return False, f"Connection error: {e}"

def login(username: str, password: str) -> tuple[bool, str]:
    """Retrieves standard OAuth2 access tokens using user credentials."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/auth/token",
            data={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state["token"] = data["access_token"]
            st.session_state["username"] = username
            return True, "Login successful."
        else:
            detail = response.json().get("detail", "Invalid username or password.")
            return False, detail
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False, f"Connection error: {e}"

# ==============================================================================
# CORPORA CRUD HANDLERS
# ==============================================================================
def list_corpora() -> list:
    """Retrieves list of corpora owned by authenticated user."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/corpora/",
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"List corpora error: {e}")
        return []

def create_corpus(name: str) -> dict | None:
    """Creates a new document corpus logically scoped under the calling user."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/corpora/",
            headers=get_headers(),
            json={"name": name},
            timeout=10
        )
        if response.status_code == 201:
            return response.json()
        elif response.status_code == 400:
            st.warning(response.json().get("detail", "Failed to create corpus."))
        return None
    except Exception as e:
        logger.error(f"Create corpus error: {e}")
        return None

def delete_corpus(corpus_id: int) -> bool:
    """Deletes a target corpus and all nested resources."""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/corpora/{corpus_id}",
            headers=get_headers(),
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Delete corpus error: {e}")
        return False

# ==============================================================================
# DOCUMENT INGESTION HANDLERS
# ==============================================================================
def list_documents(corpus_id: int) -> list:
    """Lists files uploaded to selected corpus with processing states."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/corpora/{corpus_id}/documents",
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"List documents error: {e}")
        return []

def upload_document(corpus_id: int, filename: str, content: bytes) -> dict | None:
    """Posts a binary file payload to trigger background text parsing and vector indexing."""
    try:
        files = {"file": (filename, content)}
        response = requests.post(
            f"{BACKEND_URL}/api/corpora/{corpus_id}/documents",
            headers=get_headers(),
            files=files,
            timeout=30
        )
        if response.status_code == 202:
            return response.json()
        elif response.status_code == 400:
            st.error(response.json().get("detail", "Upload failed."))
        return None
    except Exception as e:
        logger.error(f"Upload document error: {e}")
        return None

def delete_document(corpus_id: int, document_id: int) -> bool:
    """Deletes a target document metadata and vector index from backend."""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/corpora/{corpus_id}/documents/{document_id}",
            headers=get_headers(),
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Delete document error: {e}")
        return False

# ==============================================================================
# CHAT SESSIONS CRUD HANDLERS
# ==============================================================================
def list_chat_sessions(corpus_id: int) -> list:
    """Retrieves all chat sessions associated with selected corpus."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/chat/sessions",
            headers=get_headers(),
            params={"corpus_id": corpus_id},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"List chat sessions error: {e}")
        return []

def create_chat_session(corpus_id: int, title: str) -> dict | None:
    """Adds a new chat session to partition conversation logs."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat/sessions",
            headers=get_headers(),
            json={"corpus_id": corpus_id, "title": title},
            timeout=10
        )
        if response.status_code == 201:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Create chat session error: {e}")
        return None

def delete_chat_session(session_id: int) -> bool:
    """Purges a chat session and nested messages."""
    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/chat/sessions/{session_id}",
            headers=get_headers(),
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Delete chat session error: {e}")
        return False

# ==============================================================================
# MESSAGES & RAG QUERY HANDLERS
# ==============================================================================
def list_messages(session_id: int) -> list:
    """Retrieves messages logs from the database for the active chat session."""
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/chat/sessions/{session_id}/messages",
            headers=get_headers(),
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"List messages error: {e}")
        return []

def send_message(session_id: int, query: str) -> dict | None:
    """Posts user query to execute vector-search retrieval and Groq generation."""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/chat/sessions/{session_id}/messages",
            headers=get_headers(),
            json={"message": query},
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(response.json().get("detail", "Error querying RAG server."))
            return None
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None
