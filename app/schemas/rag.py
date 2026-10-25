"""Схеми для RAG-запитів, джерел та потокових подій."""

from typing import List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Запит користувача до бази знань."""
    question: str = Field(..., min_length=3, max_length=1000, description="Запитання користувача")
    document_ids: Optional[List[str]] = Field(default=None, description="Список ID документів для фільтрації")
    top_k: Optional[int] = Field(default=None, ge=1, le=10, description="Кількість чанків для пошуку")


class SourceItem(BaseModel):
    """Знайдене джерело з інформацією про файл, сторінку та релевантність."""
    document_id: str
    filename: str
    page: Optional[int] = None
    score: float
    snippet: str


class AskResponse(BaseModel):
    """Відповідь на запитання разом зі списком джерел."""
    answer: str
    sources: List[SourceItem]


class TokenEvent(BaseModel):
    """Потоковий токен відповіді для SSE."""
    text: str


class ErrorEvent(BaseModel):
    """Повідомлення про помилку під час генерації."""
    error: str
