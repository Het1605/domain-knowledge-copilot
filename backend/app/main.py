from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import Base, engine

# Import all models to ensure they are registered with Base metadata
from backend.app.models import user, corpus, chat

app = FastAPI(
    title="Domain Knowledge Co-Pilot API",
    description="Backend REST API managing user authentication, corpora uploads, vector embeddings, and RAG chats.",
    version="1.0.0"
)

# Configure CORS Middleware for Streamlit interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Automatically generate SQLite database tables upon application boot
    Base.metadata.create_all(bind=engine)

@app.get("/health", tags=["Health"])
def health_check():
    """Simple status check verifying the API is up and running."""
    return {
        "status": "healthy",
        "app": "Domain Knowledge Co-Pilot API"
    }
