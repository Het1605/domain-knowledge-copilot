# Capstone Project Context: Domain Knowledge Co-Pilot

This document serves as the authoritative source of truth for the Domain Knowledge Co-Pilot Capstone Project. It outlines goals, constraints, stack, priorities, architecture, and decision rules.

---

## 1. Project Goal
Build a chat application that answers questions over a user's own document corpus using Retrieval-Augmented Generation (RAG), while providing citations that link back to the exact source passage.

*   **Core Value Proposition:** Replace the tedious workflow of *Search Folder → Open PDF → Ctrl+F → Read* with a seamless *Ask Question → Get Answer → Verify Citation* interface.
*   **Key Behavior:** Answer questions **only** from uploaded documents and allow users to verify exactly where the answers came from.

---

## 2. Key Constraints & Philosophy
*   **Timeframe:** 15-day capstone project.
*   **Primary Objective:** Deliver a complete, working, and deployable project following capstone requirements.
*   **Simplicity:** Avoid unnecessary complexity and feature creep. Prioritize completing mandatory requirements before considering stretch features.
*   **Scope Boundaries (Non-Goals):**
    *   **NO** LangGraph or multi-agent workflows.
    *   **NO** voice or image processing/vision/OCR.
    *   **NO** external vector databases (e.g., Pinecone, Weaviate, Qdrant) or graph databases (Neo4j).
    *   **NO** local LLM runners (Ollama).
    *   **NO** email or notification systems.

---

## 3. Core Outcomes (Mandatory Requirements)
The final project must support the following:
1.  **User Authentication:** Signup and login using JWT authentication.
2.  **Corpus Ownership:** Users own their own corpora (isolated data).
3.  **File Upload Support:** PDF, DOCX, TXT, and Markdown files.
4.  **Document Processing:** Document chunking and embedding generation.
5.  **Vector Storage:** Embeddings stored in ChromaDB (one collection per corpus).
6.  **Chat Interface:** Clean UI for asking questions.
7.  **RAG-Driven Answers:** Answers generated using retrieved document chunks.
8.  **Detailed Citations:** Citations attached to LLM answers including:
    *   Filename
    *   Source chunk text
    *   Page number (where available)
9.  **Multi-Corpora Support:** Multiple corpora per user.
10. **Chat History:** Per-corpus chat history that is resumable.

---

## 4. Approved Technology Stack
Only approved technologies may be used:

*   **Frontend:** Streamlit
    *   *Preferred components:* `st.chat_input`, `st.chat_message`, sidebar corpus selector, file upload widgets.
*   **Backend:** FastAPI
*   **Authentication:** JWT
*   **Database:** SQLite with SQLAlchemy ORM
*   **Vector Database:** ChromaDB (one collection per corpus)
*   **Embeddings Model:** `sentence-transformers/all-MiniLM-L6-v2`
*   **LLM API:** Groq (Preferred model: `llama-3.3-70b-versatile`)
*   **File Parsers:** `pypdf`, `pdfplumber`, `python-docx` (use most appropriate per format)

---

## 5. System Architecture
```
[User Uploads Document]
       │
       ▼
[FastAPI Upload Endpoint] ──> [Store File Metadata in SQLite]
       │
       ▼
[Extract Text (pypdf/pdfplumber/docx)]
       │
       ▼
[Chunk Text]
       │
       ▼
[Generate Embeddings (sentence-transformers)]
       │
       ▼
[Store in ChromaDB Collection]
```

```
[User Selects Corpus & Asks Question in Streamlit]
       │
       ▼
[Embed Question (sentence-transformers)]
       │
       ▼
[Retrieve Top-K Chunks from ChromaDB]
       │
       ▼
[Load Recent Chat Context from SQLite]
       │
       ▼
[Send Combined Context + Chunks to LLM (Groq)]
       │
       ▼
[Generate Answer + Attach Citations]
       │
       ▼
[Save Chat History to SQLite]
       │
       ▼
[Return Response to Streamlit]
```

---

## 6. Development Priorities
To be followed strictly:

*   **Priority 1 (Mandatory Core):**
    *   Authentication
    *   Corpus management
    *   File upload & ingestion
    *   RAG pipeline (retrieval + generation)
    *   Citations
    *   Chat history (SQLite)
*   **Priority 2 (UX/UI Polish - only after Priority 1 is complete):**
    *   Better UI styling
    *   Retrieved chunk viewer
    *   Citation expansion/details
*   **Priority 3 (Stretch Features - only after Priority 2 is complete):**
    *   *Hybrid Retrieval (BM25 + Vector Search)* - Preferred stretch feature.
    *   Reranking, Query Reformulation, Cross-Corpus Comparison.

---

## 7. Deployment Strategy
*   **Platform:** Render (two distinct services)
    1.  **FastAPI Backend Service**
    2.  **Streamlit Frontend Service**
*   **Environment Configuration:** Must use environment variables. No hardcoded localhost URLs.
    *   `GROQ_API_KEY`
    *   `SECRET_KEY`
    *   `DATABASE_URL`
    *   `BACKEND_URL`

---

## 8. Decision Rule
When making design, implementation, database, or API choices:
1.  Follow capstone requirements first.
2.  Keep implementation simple.
3.  Prefer reliability over sophistication.
4.  Prefer completion over experimentation.
5.  Optimize for a successful 15-day delivery.
