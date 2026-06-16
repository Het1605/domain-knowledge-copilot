import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from groq import Groq

from backend.app.api import deps
from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.models.corpus import Corpus
from backend.app.models.chat import ChatSession, Message
from backend.app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionOut,
    MessageOut,
    ChatPromptIn,
    ChatResponseOut,
    CitationOut
)
from backend.app.services.vector_store import query_vector_store

logger = logging.getLogger(__name__)

router = APIRouter()

# ==============================================================================
# CHAT SESSIONS CRUD
# ==============================================================================
@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    session_in: ChatSessionCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Creates a new resumable chat session mapped under a target document corpus."""
    # 1. Verify corpus ownership
    corpus = db.query(Corpus).filter(
        Corpus.id == session_in.corpus_id,
        Corpus.owner_id == current_user.id
    ).first()
    if not corpus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corpus not found or not authorized."
        )

    # 2. Create and persist session
    session = ChatSession(
        title=session_in.title,
        corpus_id=session_in.corpus_id,
        user_id=current_user.id
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/sessions", response_model=list[ChatSessionOut])
def list_chat_sessions(
    corpus_id: Optional[int] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Retrieves all chat sessions owned by the user, optionally filtered by corpus_id."""
    query = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)
    
    if corpus_id is not None:
        # Verify corpus ownership
        corpus = db.query(Corpus).filter(Corpus.id == corpus_id, Corpus.owner_id == current_user.id).first()
        if not corpus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Corpus not found or not authorized."
            )
        query = query.filter(ChatSession.corpus_id == corpus_id)
        
    return query.all()

@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
def delete_chat_session(
    session_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Deletes a target chat session after checking ownership."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or not authorized."
        )
        
    db.delete(session)
    db.commit()
    return {"message": "Chat session successfully deleted."}

# ==============================================================================
# MESSAGES LOGS & RAG PIPELINE
# ==============================================================================
@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def list_session_messages(
    session_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Returns chronological messages history for the selected chat session."""
    # Verify session ownership
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or not authorized."
        )
        
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).all()

@router.post("/sessions/{session_id}/messages", response_model=ChatResponseOut)
def send_chat_message(
    session_id: int,
    prompt_in: ChatPromptIn,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Executes vector document search, compiles history context, and queries Groq for RAG answers with citations."""
    # 1. Verify chat session ownership
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found or not authorized."
        )

    # 2. Retrieve top relevant document chunks from ChromaDB
    retrieved_chunks = query_vector_store(
        corpus_id=session.corpus_id,
        query_text=prompt_in.message,
        n_results=5
    )

    # 3. Format context string for LLM and build citation metadata
    context_str = ""
    citations = []
    
    for i, chunk in enumerate(retrieved_chunks, 1):
        page_info = f", Page {chunk['page_number']}" if chunk.get("page_number") is not None else ""
        context_str += f"Document Chunk [{i}] (Source: {chunk['filename']}{page_info}):\n{chunk['text']}\n\n"
        
        citations.append(
            CitationOut(
                filename=chunk["filename"],
                page_number=chunk["page_number"],
                text=chunk["text"]
            )
        )

    # 4. Fetch the last 6 messages to inject conversational context
    history_records = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(6).all()
    
    # Reverse history so it's chronologically ascending
    history_records.reverse()

    # 5. Build prompt payload for Groq
    system_instruction = (
        "You are a helpful and precise Domain Knowledge Co-Pilot.\n"
        "Your task is to answer the user's question using ONLY the provided document chunks below.\n"
        "Refer to the source chunks as [1], [2], etc., corresponding to their chunk index numbers.\n"
        "If the answer cannot be found in the provided document chunks, you MUST say exactly: "
        "'I cannot find the answer in the provided documents.'\n"
        "Do not use external knowledge or make up answers. Be direct, factual, and professional.\n\n"
        "--- START PROVIDED CONTEXT ---\n"
        f"{context_str}"
        "--- END PROVIDED CONTEXT ---"
    )

    messages_payload = [
        {"role": "system", "content": system_instruction}
    ]
    for msg in history_records:
        messages_payload.append({"role": msg.role, "content": msg.content})
    messages_payload.append({"role": "user", "content": prompt_in.message})

    # 6. Execute Groq completion call
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.strip() == "your_groq_api_key_here":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Groq API key is not configured on the server. Please check the backend .env configuration."
        )

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_payload,
            temperature=0.0  # Set temperature to 0 for highest factual precision
        )
        assistant_response = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API call failure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Groq LLM endpoint failure: {str(e)}"
        )

    # 7. Write history log records to SQLite
    user_msg_record = Message(
        session_id=session_id,
        role="user",
        content=prompt_in.message,
        citations_json=None
    )
    db.add(user_msg_record)

    # Construct citations JSON list for database serialization
    citations_data = [
        {"filename": c.filename, "page_number": c.page_number, "text": c.text}
        for c in citations
    ]
    
    assistant_msg_record = Message(
        session_id=session_id,
        role="assistant",
        content=assistant_response,
        citations_json=json.dumps(citations_data)
    )
    db.add(assistant_msg_record)
    db.commit()

    return ChatResponseOut(
        role="assistant",
        content=assistant_response,
        citations=citations
    )
