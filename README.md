# Domain Knowledge Co-Pilot 🤖📚

Domain Knowledge Co-Pilot is an intelligent Retrieval-Augmented Generation (RAG) Document Assistant. It enables users to upload a custom collection of documents (PDF, DOCX, TXT, MD) and ask questions over them. The assistant provides answers based strictly on the uploaded content and includes detailed source citations with filename, passage excerpts, and page numbers.

---

## 🛠️ Technology Stack

* **Frontend**: Streamlit
* **Backend**: FastAPI (Python)
* **Authentication**: JWT (JSON Web Tokens)
* **Database**: SQLite with SQLAlchemy ORM
* **Vector Store**: ChromaDB (isolated collection per corpus)
* **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (runs locally)
* **LLM API**: Groq API (llama-3.3-70b-versatile)

---

## 📐 System Architecture

### Document Ingestion Flow (Upload)
```
[User Uploads Document]
       │
       ▼
[FastAPI Ingestion Endpoint] ──> [Save Metadata in SQLite]
       │
       ▼
[Extract Text (pypdf/pdfplumber/docx)]
       │
       ▼
[Chunk Text & Generate Embeddings]
       │
       ▼
[Store in ChromaDB Collection]
```

### Retrieval & Generation Flow (Chat)
```
[User Asks Question in Streamlit]
       │
       ▼
[Embed Question (all-MiniLM-L6-v2)]
       │
       ▼
[Retrieve Top-K Source Chunks from ChromaDB]
       │
       ▼
[Load Recent Session History from SQLite]
       │
       ▼
[Generate Answer via Groq LLM API]
       │
       ▼
[Save Conversation & Expose Excerpts + Citations to UI]
```

---

## 🚀 Local Setup & Installation

### Prerequisites
* Python 3.10 or 3.11
* A [Groq API Key](https://console.groq.com/)

### 1. Clone the Project & Configure Environment
Navigate to the root directory and create a `.env` file:
```ini
# FastAPI Backend Settings
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=your_jwt_signing_secret_here
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///backend/data/sql/db.sqlite
CHROMADB_DIR=backend/data/chromadb
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

# Streamlit Frontend Settings
BACKEND_URL=http://localhost:8000
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# or .venv\Scripts\activate     # On Windows

# Install all required Python packages
pip install -r requirements.txt
```

### 3. Run the Applications

#### Start the FastAPI Backend
```bash
python backend/run.py
```
*The backend server will run on [http://localhost:8000](http://localhost:8000).*

#### Start the Streamlit Frontend (In a new terminal window)
```bash
streamlit run frontend/app.py
```
*The frontend application will open automatically at [http://localhost:8501](http://localhost:8501).*

