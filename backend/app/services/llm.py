import json
import logging
from sqlalchemy.orm import Session
from groq import Groq

from backend.app.core.config import settings
from backend.app.models.chat import ChatSession, Message
from backend.app.schemas.chat import CitationOut
from backend.app.services.agents.nodes import classify_query_node, retrieve_context_node

logger = logging.getLogger(__name__)

def execute_rag_query_stream(db: Session, session_id: int, user_message: str):
    """Executes agent-based intent analysis and document retrieval, streams Groq response
    tokens back to the caller, and finally saves conversation logs to SQLite.
    """
    # 1. Validate API settings
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.strip() == "your_groq_api_key_here":
        raise ValueError("Groq API key is not configured on the server.")

    # 2. Retrieve the session record from SQLite
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise ValueError("Chat session not found")

    # 3. Fetch recent messages for history
    history_records = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(6).all()
    
    # Reverse history so it's chronologically ascending
    history_records.reverse()
    
    chat_history = []
    for msg in history_records:
        chat_history.append({"role": msg.role, "content": msg.content})

    # 4. Invoke Classifier and Retriever Agents directly using state dict
    state = {
        "db": db,
        "query": user_message,
        "chat_history": chat_history,
        "corpus_id": session.corpus_id,
        "intent": "specific_qa",
        "retrieved_chunks": [],
        "response_content": "",
        "citations": []
    }

    # Step A: Classify query
    classify_res = classify_query_node(state)
    state.update(classify_res)

    # Step B: Retrieve context
    retrieve_res = retrieve_context_node(state)
    state.update(retrieve_res)

    intent = state["intent"]
    retrieved_chunks = state["retrieved_chunks"]

    # 5. Format context string and build citations list
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

    # 6. Build system instructions
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

    # 7. Compile message payload
    messages_payload = [{"role": "system", "content": system_instruction}]
    for msg in chat_history:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})
    messages_payload.append({"role": "user", "content": user_message})

    # 8. Call Groq streaming API and yield tokens
    full_response_text = ""
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages_payload,
            temperature=0.0,
            stream=True
        )
        for chunk in completion:
            delta = chunk.choices[0].delta.content
            if delta:
                full_response_text += delta
                yield delta
    except Exception as e:
        logger.error(f"Failed to generate streaming RAG response: {e}", exc_info=True)
        err_msg = "\nI encountered an error generating a response."
        full_response_text += err_msg
        yield err_msg

    # 9. Save conversation message logs to SQLite after completion
    user_msg_record = Message(
        session_id=session_id,
        role="user",
        content=user_message,
        citations_json=None
    )
    db.add(user_msg_record)

    citations_data = [
        {"filename": c.filename, "page_number": c.page_number, "text": c.text}
        for c in citations
    ]
    
    assistant_msg_record = Message(
        session_id=session_id,
        role="assistant",
        content=full_response_text,
        citations_json=json.dumps(citations_data)
    )
    db.add(assistant_msg_record)
    db.commit()
