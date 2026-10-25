"""Схеми запитів та відповідей для роботи з документами."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    """Відповідь після прийняття файлу на обробку."""
    id: str
    status: DocumentStatus


class DocumentListItem(BaseModel):
    """Елемент списку документів у системі."""
    id: str
    filename: str
    status: DocumentStatus
    chunks_count: int
    created_at: datetime


class DocumentDetailResponse(BaseModel):
    """Детальна інформація про конкретний документ."""
    id: str
    filename: str
    status: DocumentStatus
    chunks_count: int
    file_size: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Стандартна відповідь із текстовим повідомленням."""
    message: str
