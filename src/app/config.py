"""
Configuration settings for RAGAgent Studio
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Server
    MINDSDB_HOST: str = os.getenv("MINDSDB_HOST", "http://localhost:47334")
    
    # File uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
