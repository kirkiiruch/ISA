"""Провайдери залежностей FastAPI (Dependency Injection)."""

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase
from app.ai.base import LLMClient, EmbeddingClient
from app.ai.ollama import OllamaLLMClient, OllamaEmbeddingClient
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.repositories.document_repo import DocumentRepository
from app.repositories.chunk_repo import ChunkRepository
from app.services.ingestion import IngestionService
from app.services.retrieval import RetrievalService
from app.services.rag import RAGService


def get_app_settings() -> Settings:
    """Отримати налаштування застосунку."""
    return get_settings()


def get_database(settings: Settings = Depends(get_app_settings)) -> AsyncDatabase:
    """Отримати клієнт бази даних MongoDB."""
    return get_db(settings)


def get_document_repository(db: AsyncDatabase = Depends(get_database)) -> DocumentRepository:
    """Отримати репозиторій документів."""
    return DocumentRepository(db)


def get_chunk_repository(db: AsyncDatabase = Depends(get_database)) -> ChunkRepository:
    """Отримати репозиторій текстових чанків."""
    return ChunkRepository(db)


def get_embedding_client(settings: Settings = Depends(get_app_settings)) -> EmbeddingClient:
    """Отримати клієнт ембедингів Ollama."""
    return OllamaEmbeddingClient(
        base_url=settings.OLLAMA_URL,
        model=settings.EMBEDDING_MODEL,
    )


def get_llm_client(settings: Settings = Depends(get_app_settings)) -> LLMClient:
    """Отримати клієнт мовної моделі Ollama."""
    return OllamaLLMClient(
        base_url=settings.OLLAMA_URL,
        model=settings.LLM_MODEL,
    )


def get_ingestion_service(
    doc_repo: DocumentRepository = Depends(get_document_repository),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
    settings: Settings = Depends(get_app_settings),
) -> IngestionService:
    """Отримати сервіс обробки та завантаження документів."""
    return IngestionService(
        document_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
        settings=settings,
    )


def get_retrieval_service(
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    embedding_client: EmbeddingClient = Depends(get_embedding_client),
    settings: Settings = Depends(get_app_settings),
) -> RetrievalService:
    """Отримати сервіс семантичного пошуку."""
    return RetrievalService(
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
        settings=settings,
    )


def get_rag_service(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    llm_client: LLMClient = Depends(get_llm_client),
) -> RAGService:
    """Отримати сервіс генерації відповідей за контекстом."""
    return RAGService(
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )
