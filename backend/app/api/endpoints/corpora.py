from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from backend.app.api import deps
from backend.app.models.user import User
from backend.app.models.corpus import Corpus, Document
from backend.app.schemas.corpus import CorpusCreate, CorpusOut, DocumentOut
from backend.app.services.ingestion import process_document_ingestion

router = APIRouter()

# ==============================================================================
# CORPUS CRUD MANAGEMENT
# ==============================================================================
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
    """Deletes a target corpus, checking user ownership. Cascades to remove SQLite child items and ChromaDB collection."""
    corpus = db.query(Corpus).filter(
        Corpus.id == corpus_id,
        Corpus.owner_id == current_user.id
    ).first()
    if not corpus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corpus not found or not authorized."
        )
        
    # Purge vector collection associated with the corpus
    from backend.app.services.vector_store import delete_corpus_collection
    delete_corpus_collection(corpus_id)

    db.delete(corpus)
    db.commit()
    return {"message": "Corpus successfully deleted."}

# ==============================================================================
# DOCUMENT UPLOAD & LIST INGESTION MANAGEMENT
# ==============================================================================
@router.post("/{corpus_id}/documents", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    corpus_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Accepts document uploads (PDF, DOCX, TXT, MD) and schedules background text parsing and chunking."""
    # 1. Verify corpus ownership
    corpus = db.query(Corpus).filter(Corpus.id == corpus_id, Corpus.owner_id == current_user.id).first()
    if not corpus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corpus not found or not authorized."
        )
        
    # 2. Check if a document with identical name already exists in corpus
    existing_doc = db.query(Document).filter(
        Document.corpus_id == corpus_id,
        Document.filename == file.filename
    ).first()
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A document with this filename already exists in this corpus."
        )
        
    # Read binary bytes
    file_bytes = file.file.read()
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "TXT"
    
    # 3. Create document log inside SQLite
    db_doc = Document(
        filename=file.filename,
        file_type=ext.upper(),
        status="ingesting",
        corpus_id=corpus_id
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # 4. Delegate heavy text parsing and chunking calculations to BackgroundTask
    background_tasks.add_task(process_document_ingestion, db, db_doc.id, file_bytes)
    
    return db_doc

@router.get("/{corpus_id}/documents", response_model=list[DocumentOut])
def list_documents(
    corpus_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Retrieves all documents associated with the selected corpus."""
    # Verify corpus ownership
    corpus = db.query(Corpus).filter(Corpus.id == corpus_id, Corpus.owner_id == current_user.id).first()
    if not corpus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corpus not found or not authorized."
        )
        
    return db.query(Document).filter(Document.corpus_id == corpus_id).all()
