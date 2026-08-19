import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    PROJECT_NAME: str = "DataPulse AI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Autonomous Enterprise Product Analytics, Experimentation & Root-Cause Intelligence Agent"
    
    # LLM Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    
    # Model configuration
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "gemini")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemini-2.0-flash")
    
    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "database", "analytics.duckdb"))
    
    # Agent Parameters
    MAX_SQL_RETRIES: int = 3
    CONFIDENCE_LEVEL: float = 0.95
    SRM_ALPHA_THRESHOLD: float = 0.01

settings = Settings()
