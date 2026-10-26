"""Конфігурація застосунку та налаштування оточення."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Налаштування сервісу, бази даних MongoDB та моделей Ollama."""

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
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 150
    TOP_K: int = 5
    SCORE_THRESHOLD: float = 0.8
    MAX_FILE_SIZE_MB: int = 10

    # Application Settings
    APP_PORT: int = 8000
    STATIC_DIR: str = "app/static"


@lru_cache()
def get_settings() -> Settings:
    """Отримати кешований екземпляр налаштувань."""
    return Settings()
