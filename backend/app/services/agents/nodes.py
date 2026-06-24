import logging
from groq import Groq

from backend.app.core.config import settings
from backend.app.models.corpus import Document
from backend.app.schemas.chat import CitationOut
from backend.app.services.vector_store import query_vector_store
from .state import AgentState

logger = logging.getLogger(__name__)

# ==============================================================================
# LANGGRAPH AGENT NODES
# ==============================================================================
def classify_query_node(state: AgentState) -> dict:
    """Classifies the user query intent to route context retrieval appropriately."""
    query = state["query"]
    
    # Compile short history context for classification
    history_str = ""
    for msg in state["chat_history"][-3:]:
        history_str += f"{msg['role']}: {msg['content']}\n"
        
    classify_prompt = (
        "You are an AI assistant classifying user query intent for a document search system.\n"
        "Analyze the user query (and recent history context) to classify it into exactly one of these categories:\n"
        "- 'summary': if the user wants an overview, list, or summary of the documents, files, or corpus.\n"
        "- 'specific_qa': if the user is asking a specific factual question about document contents.\n"
        "- 'general': if the user is greeting you, asking about you, or asking general questions unrelated to the uploaded documents.\n\n"
        "Output ONLY the category name ('summary', 'specific_qa', or 'general') in lowercase, with no other text.\n\n"
        f"Recent History:\n{history_str}\n"
        f"User Query: \"{query}\"\n"
        "Category:"
    )

    intent = "specific_qa"  # Default fallback
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": classify_prompt}],
            temperature=0.0
        )
        result = completion.choices[0].message.content.strip().lower()
        if result in ["summary", "specific_qa", "general"]:
            intent = result
    except Exception as e:
        logger.error(f"Failed to classify query: {e}", exc_info=True)
        
    logger.info(f"Query classified as intent: {intent}")
    return {"intent": intent}

def retrieve_context_node(state: AgentState) -> dict:
    """Retrieves document context based on the classified user intent."""
    intent = state["intent"]
    corpus_id = state["corpus_id"]
    query = state["query"]
    db = state["db"]

    retrieved_chunks = []
    
    # Fetch all completed documents in SQLite
    completed_docs = db.query(Document).filter(
        Document.corpus_id == corpus_id,
        Document.status == "completed"
    ).all()

    if not completed_docs:
        logger.info("No completed documents found in corpus. Skipping retrieval.")
        return {"retrieved_chunks": []}

    if intent == "summary":
        # For summaries, we want chunks from *every* completed document
        num_docs = len(completed_docs)
        chunks_per_doc = 4 if num_docs <= 3 else (3 if num_docs <= 6 else 2)
        
        for doc in completed_docs:
            doc_chunks = query_vector_store(
                corpus_id=corpus_id,
                query_text=query,
                n_results=chunks_per_doc,
                document_id=doc.id
            )
            retrieved_chunks.extend(doc_chunks)
            
    elif intent == "specific_qa":
        # For specific QA, query ChromaDB globally to find top matching chunks
        retrieved_chunks = query_vector_store(
            corpus_id=corpus_id,
            query_text=query,
            n_results=8
        )
        
    # For "general" intent, retrieved_chunks remains empty.
    
    logger.info(f"Retrieved {len(retrieved_chunks)} chunks for intent '{intent}'")
    return {"retrieved_chunks": retrieved_chunks}

def generate_response_node(state: AgentState) -> dict:
    """Formulates the final synthesized response based on context and classified intent."""
    intent = state["intent"]
    query = state["query"]
    retrieved_chunks = state["retrieved_chunks"]
    chat_history = state["chat_history"]

    # 1. Format context string and build citations list
    context_str = ""
    citations = []
    for chunk in retrieved_chunks:
        page_info = f", Page {chunk['page_number']}" if chunk.get("page_number") is not None else ""
        context_str += f"Document Chunk (Source: {chunk['filename']}{page_info}):\n{chunk['text']}\n\n"
        
        citations.append(
            CitationOut(
                filename=chunk["filename"],
                page_number=chunk["page_number"],
                text=chunk["text"]
            )
        )

    # 2. Build system instructions
    if intent == "general":
        system_instruction = (
            "You are an advanced Domain Knowledge Co-Pilot.\n\n"
            "The user is engaging in general conversation (greetings, general chat, or questions unrelated to uploaded files).\n"
            "Respond naturally, politely, and intelligently. Do not refer to any documents or lookups since none are available."
        )
    else:
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

    # 3. Compile message payload
    messages_payload = [{"role": "system", "content": system_instruction}]
    for msg in chat_history:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})
    messages_payload.append({"role": "user", "content": query})

    # 4. Invoke Groq
    response_content = "I encountered an error generating a response."
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_payload,
            temperature=0.0
        )
        response_content = completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Failed to generate RAG response: {e}", exc_info=True)

    return {
        "response_content": response_content,
        "citations": citations
    }
