import io
import logging
import pdfplumber
import docx
from docx.text.paragraph import Paragraph
from docx.table import Table
from sqlalchemy.orm import Session
from backend.app.models.corpus import Document

# Set up backend logs
logger = logging.getLogger(__name__)

# ==============================================================================
# TEXT EXTRACTION HELPERS WITH TABLE SUPPORT
# ==============================================================================
def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, list[dict]]:
    """Extracts text and tables page-by-page from PDF bytes using pdfplumber.
    
    Returns:
        tuple containing (full_extracted_text, list of dictionaries mapping page content)
    """
    text_list = []
    pages_data = []
    pdf_file = io.BytesIO(file_bytes)
    
    with pdfplumber.open(pdf_file) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = page.extract_text() or ""
            
            # Extract tables layout if present on the page
            tables_text = ""
            try:
                tables = page.extract_tables()
                for table in tables:
                    table_rows = []
                    for row in table:
                        clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        if any(clean_row):
                            table_rows.append(" | ".join(clean_row))
                    if table_rows:
                        tables_text += "\n\n[Table Context]\n" + "\n".join(table_rows) + "\n"
            except Exception as e:
                logger.warning(f"Error extracting tables on PDF page {page_num}: {e}")
            
            full_page_text = page_text
            if tables_text:
                full_page_text += tables_text
                
            if full_page_text.strip():
                text_list.append(full_page_text)
                pages_data.append({
                    "page_number": page_num,
                    "text": full_page_text
                })
                
    return "\n".join(text_list), pages_data

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text paragraphs and tables from Word document bytes, maintaining order."""
    docx_file = io.BytesIO(file_bytes)
    doc = docx.Document(docx_file)
    text = []
    
    # Iterate over child elements in doc.element.body to preserve logical layout order
    for child in doc.element.body:
        name = child.tag.split("}")[-1]
        if name == "p":
            p = Paragraph(child, doc)
            if p.text.strip():
                text.append(p.text.strip())
        elif name == "tbl":
            t = Table(child, doc)
            table_rows = []
            for row in t.rows:
                # Deduplicate cells matching merges
                row_cells = []
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if not row_cells or row_cells[-1] != cell_text:
                        row_cells.append(cell_text)
                if any(row_cells):
                    table_rows.append(" | ".join(row_cells))
            if table_rows:
                text.append("\n[Table Context]\n" + "\n".join(table_rows) + "\n")
                
    return "\n".join(text)

def extract_text_from_txt_or_md(file_bytes: bytes) -> str:
    """Decodes plain text or markdown string from file bytes."""
    return file_bytes.decode("utf-8", errors="ignore")

# ==============================================================================
# RECURSIVE CHARACTER TEXT CHUNKER
# ==============================================================================
def recursive_chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """Splits raw text strings into chunks recursively based on logical boundaries
    like paragraphs, sentences, and words to preserve sentence structures.
    """
    if not text:
        return []
        
    separators = ["\n\n", "\n", " ", ""]
    
    def split_text(text_str: str, separators_list: list[str]) -> list[str]:
        if len(text_str) <= chunk_size:
            return [text_str]
            
        if not separators_list:
            # Fallback splitter
            return [text_str[i:i + chunk_size] for i in range(0, len(text_str), chunk_size)]
            
        separator = separators_list[0]
        if separator == "":
            splits = list(text_str)
        else:
            splits = text_str.split(separator)
            
        chunks = []
        current_chunk = ""
        
        for split in splits:
            item = split + (separator if separator != "" else "")
            
            if len(item) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.extend(split_text(split, separators_list[1:]))
            elif len(current_chunk) + len(item) <= chunk_size:
                current_chunk += item
            else:
                chunks.append(current_chunk.strip())
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                current_chunk = overlap_text + item
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return [c for c in chunks if c.strip()]
        
    return split_text(text, separators)

# ==============================================================================
# BACKGROUND INGESTION WORKER
# ==============================================================================
def process_document_ingestion(db: Session, doc_id: int, file_bytes: bytes):
    """Background worker task extracting text and splitting chunks."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        logger.error(f"Background worker: Document {doc_id} not found in database.")
        return

    try:
        logger.info(f"Ingestion started for document {doc_id} ({doc.filename})")
        ext = doc.filename.split(".")[-1].lower() if "." in doc.filename else ""
        
        page_chunks = []  # list of tuples: (chunk_text, page_number_or_none)
        
        if ext == "pdf":
            _, pages_data = extract_text_from_pdf(file_bytes)
            for page in pages_data:
                chunks = recursive_chunk_text(page["text"], chunk_size=1000, chunk_overlap=150)
                for chunk in chunks:
                    if chunk.strip():
                        page_chunks.append((chunk.strip(), page["page_number"]))
                        
        elif ext == "docx":
            full_text = extract_text_from_docx(file_bytes)
            chunks = recursive_chunk_text(full_text, chunk_size=1000, chunk_overlap=150)
            for chunk in chunks:
                if chunk.strip():
                    page_chunks.append((chunk.strip(), None))
                    
        elif ext in ("txt", "md"):
            full_text = extract_text_from_txt_or_md(file_bytes)
            chunks = recursive_chunk_text(full_text, chunk_size=1000, chunk_overlap=150)
            for chunk in chunks:
                if chunk.strip():
                    page_chunks.append((chunk.strip(), None))
                    
        else:
            full_text = file_bytes.decode("utf-8", errors="ignore")
            chunks = recursive_chunk_text(full_text, chunk_size=1000, chunk_overlap=150)
            for chunk in chunks:
                if chunk.strip():
                    page_chunks.append((chunk.strip(), None))

        # Output logging verification info
        logger.info(f"Successfully extracted {len(page_chunks)} chunks for document {doc_id}.")

        # Store chunks and embeddings in ChromaDB
        if page_chunks:
            from backend.app.services.vector_store import add_document_chunks
            add_document_chunks(
                corpus_id=doc.corpus_id,
                document_id=doc.id,
                filename=doc.filename,
                chunks=page_chunks
            )
        else:
            raise ValueError("No text could be extracted from this document (it might be scanned, empty, or unparseable).")

        # Update status inside SQLite
        doc.status = "completed"
        db.commit()
        logger.info(f"Ingestion completed successfully for document {doc_id} ({doc.filename})")
        
    except Exception as e:
        doc.status = "failed"
        db.commit()
        logger.error(f"Ingestion failed for document {doc_id}: {str(e)}", exc_info=True)
