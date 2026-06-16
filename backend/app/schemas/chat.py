from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ChatSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150, description="The descriptive title of the chat session")
    corpus_id: int = Field(..., description="The ID of the corpus this session is scoped under")

class ChatSessionOut(BaseModel):
    id: int
    title: str
    corpus_id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    citations_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatPromptIn(BaseModel):
    message: str = Field(..., min_length=1, description="The user's query prompt text")

class CitationOut(BaseModel):
    filename: str
    page_number: Optional[int] = None
    text: str

class ChatResponseOut(BaseModel):
    role: str = "assistant"
    content: str
    citations: list[CitationOut]
