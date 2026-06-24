import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api import deps
from backend.app.models.user import User
from backend.app.models.corpus import Corpus
from backend.app.models.chat import ChatSession, Message
from backend.app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionOut,
    MessageOut,
    ChatPromptIn,
    ChatResponseOut
)
from backend.app.services.llm import execute_rag_query

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

    try:
        response = execute_rag_query(db, session_id, prompt_in.message)
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing query: {str(e)}"
        )
