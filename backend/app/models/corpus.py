from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Corpus(Base):
    __tablename__ = "corpora"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="corpora" if hasattr(Base, "User") else None, backref="corpora")

    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_owner_corpus_name"),
    )

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    status = Column(String(20), default="ingesting", nullable=False)
    corpus_id = Column(Integer, ForeignKey("corpora.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    corpus = relationship("Corpus", backref="documents")

    __table_args__ = (
        UniqueConstraint("corpus_id", "filename", name="uq_corpus_filename"),
    )
