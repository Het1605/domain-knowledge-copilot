import json
import logging
from sqlalchemy.orm import Session
from groq import Groq

from backend.app.core.config import settings
from backend.app.models.corpus import Document
from backend.app.models.chat import ChatSession, Message
from backend.app.schemas.chat import ChatResponseOut, CitationOut
from backend.app.services.vector_store import query_vector_store

logger = logging.getLogger(__name__)

def execute_rag_query(db: Session, session_id: int, user_message: str) -> ChatResponseOut:
    """Retrieves top relevant chunks from ChromaDB, constructs context, 
    injects history, and queries the Groq LLM with a reasoning-focused prompt.
    Saves the user and assistant messages to SQLite.
    """
    # 1. Retrieve the session record from SQLite
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise ValueError("Chat session not found")

    # 2. Retrieve top relevant document chunks from ChromaDB per document to guarantee coverage
    completed_docs = db.query(Document).filter(
        Document.corpus_id == session.corpus_id,
        Document.status == "completed"
    ).all()

    retrieved_chunks = []
    if completed_docs:
        num_docs = len(completed_docs)
        # Scale chunks per document to avoid oversized context windows
        chunks_per_doc = 4 if num_docs <= 3 else (3 if num_docs <= 6 else 2)
        
        for doc in completed_docs:
            doc_chunks = query_vector_store(
                corpus_id=session.corpus_id,
                query_text=user_message,
                n_results=chunks_per_doc,
                document_id=doc.id
            )
            retrieved_chunks.extend(doc_chunks)

    # 3. Format context string and build citations
    context_str = ""
    citations = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        page_info = f", Page {chunk['page_number']}" if chunk.get("page_number") is not None else ""
        context_str += f"Document Chunk [{i}] (Source: {chunk['filename']}{page_info}):\n{chunk['text']}\n\n"
        
        citations.append(
            CitationOut(
                filename=chunk["filename"],
                page_number=chunk["page_number"],
                text=chunk["text"]
            )
        )

    # 4. Fetch the last 6 messages for conversation context
    history_records = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(6).all()
    
    # Reverse history so it's chronologically ascending
    history_records.reverse()

    # 5. Build prompt payload for Groq with improved reasoning instruction
    system_instruction = (
        "You are an advanced, reasoning-focused Domain Knowledge Co-Pilot.\n\n"
        "Your goal is to fully understand the user's query and provide a well-structured, synthesized, "
        "and accurate response based ONLY on the provided document context.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. INTENT ANALYSIS: First, determine what the user is asking (e.g., a summary, a comparison, a specific fact, or an explanation). Align your response structure to fulfill this intent perfectly.\n"
        "2. CONCEPT SYNTHESIS & REASONING: Read all provided document chunks carefully. Explain concepts, connect related ideas, and reason about the information. Avoid simple copy-pasting or presenting fragmented lists of chunks. Make the response read like a cohesive, professional write-up.\n"
        "3. NO INLINE CITATION NUMBERS: Do NOT write any reference numbers, brackets (such as [1], [2], [3]), or source indexes in your response text. The final output must be completely clean prose, free of numeric citation markers.\n"
        "4. STRICT GROUNDING: Base your answer strictly on the provided context. If the context does not contain enough information to answer the query, or if you cannot reason the answer from it, reply with exactly:\n"
        "\"I cannot find the answer in the provided documents.\"\n"
        "5. TRUTHFULNESS: Do not assume, hallucinate, or extrapolate beyond the facts present in the context.\n\n"
        "--- START PROVIDED CONTEXT ---\n"
        f"{context_str}"
        "--- END PROVIDED CONTEXT ---"
    )

    messages_payload = [
        {"role": "system", "content": system_instruction}
    ]
    for msg in history_records:
        messages_payload.append({"role": msg.role, "content": msg.content})
    messages_payload.append({"role": "user", "content": user_message})

    # 6. Execute Groq completion call
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.strip() == "your_groq_api_key_here":
        raise ValueError("Groq API key is not configured on the server.")

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_payload,
            temperature=0.0  # Factual precision
        )
        assistant_response = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API call failure: {e}", exc_info=True)
        raise e

    # 7. Write history log records to SQLite
    user_msg_record = Message(
        session_id=session_id,
        role="user",
        content=user_message,
        citations_json=None
    )
    db.add(user_msg_record)

    # Construct citations JSON list for database serialization
    citations_data = [
        {"filename": c.filename, "page_number": c.page_number, "text": c.text}
        for c in citations
    ]
    
    assistant_msg_record = Message(
        session_id=session_id,
        role="assistant",
        content=assistant_response,
        citations_json=json.dumps(citations_data)
    )
    db.add(assistant_msg_record)
    db.commit()

    return ChatResponseOut(
        role="assistant",
        content=assistant_response,
        citations=citations
    )
