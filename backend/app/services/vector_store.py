import logging
import chromadb
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

# Initialize persistent ChromaDB client (it creates the directory automatically)
logger.info(f"Initializing persistent ChromaDB client at: {settings.CHROMADB_DIR}")
chroma_client = chromadb.PersistentClient(path=settings.CHROMADB_DIR)

# Initialize global sentence embeddings model
logger.info("Initializing SentenceTransformer model 'all-MiniLM-L6-v2'...")
try:
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("SentenceTransformer model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}", exc_info=True)
    raise e

def add_document_chunks(corpus_id: int, document_id: int, filename: str, chunks: list[tuple[str, int | None]]):
    """Generates embeddings for extracted document chunks and writes them into ChromaDB.
    
    Collection names are isolated per corpus using the format: `corpus_{corpus_id}`
    """
    if not chunks:
        logger.warning(f"No chunks provided for document {document_id} ({filename}). Skipping vector indexing.")
        return

    collection_name = f"corpus_{corpus_id}"
    logger.info(f"Indexing {len(chunks)} chunks into ChromaDB collection '{collection_name}'")
    
    # Get or create the isolated collection
    collection = chroma_client.get_or_create_collection(name=collection_name)

    # Extract chunk text strings
    texts = [chunk[0] for chunk in chunks]

    # Generate vector embeddings locally
    embeddings = embedding_model.encode(texts).tolist()

    # Build metadata payloads and unique IDs
    metadatas = []
    ids = []
    
    for i, (text, page_number) in enumerate(chunks):
        meta = {
            "document_id": document_id,
            "filename": filename,
            "page_number": page_number if page_number is not None else -1
        }
        metadatas.append(meta)
        ids.append(f"doc_{document_id}_chunk_{i}")

    # Write to ChromaDB
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    logger.info(f"Successfully indexed document {document_id} chunks in collection '{collection_name}'")

def query_vector_store(corpus_id: int, query_text: str, n_results: int = 5, document_id: int = None) -> list[dict]:
    """Retrieves the top-K relevant chunks for a user query from the corpus collection,
    optionally filtered by a specific document_id.
    """
    collection_name = f"corpus_{corpus_id}"
    
    try:
        collection = chroma_client.get_collection(name=collection_name)
    except Exception:
        logger.warning(f"ChromaDB collection '{collection_name}' does not exist. Returning empty results.")
        return []

    # Embed query string
    query_embedding = embedding_model.encode([query_text]).tolist()

    # Build filter if document_id is provided
    where_clause = {"document_id": document_id} if document_id is not None else None

    # Query ChromaDB collection
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_clause
    )

    formatted_results = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else []
        distances = results["distances"][0] if "distances" in results and results["distances"] else []

        for i in range(len(docs)):
            meta = metas[i] if i < len(metas) else {}
            page_number = meta.get("page_number")
            if page_number == -1:
                page_number = None

            formatted_results.append({
                "text": docs[i],
                "filename": meta.get("filename", "Unknown"),
                "page_number": page_number,
                "distance": distances[i] if i < len(distances) else None
            })
            
    return formatted_results

def delete_corpus_collection(corpus_id: int):
    """Deletes the ChromaDB collection associated with the target corpus id."""
    collection_name = f"corpus_{corpus_id}"
    try:
        chroma_client.delete_collection(name=collection_name)
        logger.info(f"Purged ChromaDB collection '{collection_name}' successfully.")
    except Exception as e:
        logger.warning(f"Could not delete ChromaDB collection '{collection_name}': {e}")

def delete_document_chunks(corpus_id: int, document_id: int):
    """Deletes all vectorized chunks matching the target document_id from the corpus collection."""
    collection_name = f"corpus_{corpus_id}"
    try:
        collection = chroma_client.get_collection(name=collection_name)
        collection.delete(where={"document_id": document_id})
        logger.info(f"Purged chunks for document {document_id} from ChromaDB collection '{collection_name}'")
    except Exception as e:
        logger.warning(f"Could not delete document {document_id} chunks from ChromaDB: {e}")
