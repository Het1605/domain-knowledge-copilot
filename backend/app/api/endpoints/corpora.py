from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.api import deps
from backend.app.models.user import User
from backend.app.models.corpus import Corpus
from backend.app.schemas.corpus import CorpusCreate, CorpusOut

router = APIRouter()

@router.post("/", response_model=CorpusOut, status_code=status.HTTP_201_CREATED)
def create_corpus(
    corpus_in: CorpusCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Creates a new document corpus logically scoped under the calling authenticated User."""
    existing = db.query(Corpus).filter(
        Corpus.owner_id == current_user.id,
        Corpus.name == corpus_in.name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A corpus with this name already exists."
        )
        
    db_corpus = Corpus(name=corpus_in.name, owner_id=current_user.id)
    db.add(db_corpus)
    db.commit()
    db.refresh(db_corpus)
    return db_corpus

@router.get("/", response_model=list[CorpusOut])
def list_corpora(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Retrieves all corpora owned by the current authenticated User."""
    return db.query(Corpus).filter(Corpus.owner_id == current_user.id).all()

@router.delete("/{corpus_id}", status_code=status.HTTP_200_OK)
def delete_corpus(
    corpus_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Deletes a target corpus, checking user ownership. Cascades to remove SQLite child items."""
    corpus = db.query(Corpus).filter(
        Corpus.id == corpus_id,
        Corpus.owner_id == current_user.id
    ).first()
    if not corpus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corpus not found or not authorized."
        )
        
    db.delete(corpus)
    db.commit()
    return {"message": "Corpus successfully deleted."}
