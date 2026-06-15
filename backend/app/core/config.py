import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API & Auth Credentials
    GROQ_API_KEY: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # DB Persistence Configurations
    DATABASE_URL: str = "sqlite:///backend/data/sql/db.sqlite"
    CHROMADB_DIR: str = "backend/data/chromadb"
    
    # CORS allowed origins (comma-separated values)
    CORS_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parses the CORS origins comma-separated string into a list of strings."""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

# Global settings instance
settings = Settings()
