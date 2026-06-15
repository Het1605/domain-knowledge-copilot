import io
import logging
import pypdf
import docx
from sqlalchemy.orm import Session
from backend.app.models.corpus import Document

# Set up backend logs
logger = logging.getLogger(__name__)

# ==============================================================================
# TEXT EXTRACTION HELPERS
# ==============================================================================
def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, list[dict]]:
    """Extracts text page-by-page from PDF bytes.
    
    Returns:
        tuple containing (full_extracted_text, list of dictionaries mapping page content)
    """
    text_list = []
    pages_data = []
    pdf_file = io.BytesIO(file_bytes)
    reader = pypdf.PdfReader(pdf_file)
    
    for page_num, page in enumerate(reader.pages, 1):
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_list.append(page_text)
            pages_data.append({
                "page_number": page_num,
                "text": page_text
            })
            
    return "\n".join(text_list), pages_data

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text paragraph-by-paragraph from Word document bytes."""
    docx_file = io.BytesIO(file_bytes)
    doc = docx.Document(docx_file)
    text = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)
    return "\n".join(text)

def extract_text_from_txt_or_md(file_bytes: bytes) -> str:
    """Decodes plain text or markdown string from file bytes."""
    return file_bytes.decode("utf-8", errors="ignore")

# ==============================================================================
# TEXT CHUNKER UTIL
# ==============================================================================
def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """Splits raw text strings into overlapping chunk fragments."""
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
        
    return chunks

# ==============================================================================
# BACKGROUND INGESTION WORKER
# ==============================================================================
def process_document_ingestion(db: Session, doc_id: int, file_bytes: bytes):
    """Background worker task extracting text and splitting chunks.
    
    (Vector index loading to ChromaDB will be added here in Milestone 5).
    """
    # Query target document from SQLite
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        logger.error(f"Background worker: Document {doc_id} not found in database.")
        return

    try:
        logger.info(f"Ingestion started for document {doc_id} ({doc.filename})")
        ext = doc.filename.split(".")[-1].lower() if "." in doc.filename else ""
        
        # 1. Parse and compile chunk-to-page metadata mappings
        page_chunks = []  # list of tuples: (chunk_text, page_number_or_none)
        
        if ext == "pdf":
            _, pages_data = extract_text_from_pdf(file_bytes)
            for page in pages_data:
                chunks = chunk_text(page["text"])
                for chunk in chunks:
                    if chunk.strip():
                        page_chunks.append((chunk.strip(), page["page_number"]))
                        
        elif ext == "docx":
            full_text = extract_text_from_docx(file_bytes)
            chunks = chunk_text(full_text)
            for chunk in chunks:
                if chunk.strip():
                    page_chunks.append((chunk.strip(), None))
                    
        elif ext in ("txt", "md"):
            full_text = extract_text_from_txt_or_md(file_bytes)
            chunks = chunk_text(full_text)
            for chunk in chunks:
                if chunk.strip():
                    page_chunks.append((chunk.strip(), None))
                    
        else:
            # General fallback decode
            full_text = file_bytes.decode("utf-8", errors="ignore")
            chunks = chunk_text(full_text)
            for chunk in chunks:
                if chunk.strip():
                    page_chunks.append((chunk.strip(), None))

        # Output logging verification info
        logger.info(f"Successfully extracted {len(page_chunks)} chunks for document {doc_id}.")

        # 2. Update status inside SQLite
        doc.status = "completed"
        db.commit()
        logger.info(f"Ingestion completed successfully for document {doc_id} ({doc.filename})")
        
    except Exception as e:
        doc.status = "failed"
        db.commit()
        logger.error(f"Ingestion failed for document {doc_id}: {str(e)}", exc_info=True)
