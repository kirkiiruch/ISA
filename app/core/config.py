from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MongoDB Settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "knowledge_base"

    # Ollama Settings
    OLLAMA_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3.2:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # RAG Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 3
    SCORE_THRESHOLD: float = 0.5
    MAX_FILE_SIZE_MB: int = 10

    # Application Settings
    APP_PORT: int = 8000
    STATIC_DIR: str = "app/static"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
