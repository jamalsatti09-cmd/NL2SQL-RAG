from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Settings configuration class for the NL2SQL-RAG pipeline.
    Loads configurations from environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM backends — at least ONE must be set
    GROQ_API_KEY: Optional[str] = None       # FREE: https://console.groq.com  ⭐ Recommended
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None     # Free tier: https://aistudio.google.com/apikey

    # Local LLM via Ollama
    USE_LOCAL_LLM: bool = False
    OLLAMA_MODEL: str = "llama3.1:8b"

    # Vector store
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Retrieval
    TOP_K_SCHEMA: int = 10
    TOP_K_FEWSHOT: int = 5
    USE_RERANKER: bool = False

    # Execution
    MAX_RETRIES: int = 2
    ALLOW_EMPTY_RESULTS: bool = True
    DEFAULT_DB_URL: str = "sqlite:///./test.db"

    # Logging
    LOG_LEVEL: str = "INFO"


# Instantiate settings
settings = Settings()
