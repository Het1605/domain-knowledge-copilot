from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.api.endpoints.auth import router as auth_router
from backend.app.api.endpoints.corpora import router as corpora_router
from backend.app.api.endpoints.chat import router as chat_router

# Import all models to ensure they are registered with Base metadata
from backend.app.models import user, corpus, chat as chat_model

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

# Mount Routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(corpora_router, prefix="/api/corpora", tags=["Corpora Management"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat Engine"])

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
