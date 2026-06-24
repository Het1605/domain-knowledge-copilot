from typing import TypedDict, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.schemas.chat import CitationOut

class AgentState(TypedDict):
    db: Session
    query: str
    chat_history: List[Dict[str, str]]
    corpus_id: int
    intent: str  # "summary" | "specific_qa" | "general"
    retrieved_chunks: List[Dict[str, Any]]
    response_content: str
    citations: List[CitationOut]
