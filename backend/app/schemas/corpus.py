from datetime import datetime
from pydantic import BaseModel, Field

class CorpusBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="The name/label of the document corpus")

class CorpusCreate(CorpusBase):
    pass

class CorpusOut(CorpusBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        # Enable ORM attribute loading from SQLAlchemy Corpus objects
        from_attributes = True

class DocumentOut(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    corpus_id: int
    created_at: datetime

    class Config:
        from_attributes = True
