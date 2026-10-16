from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    id: str
    status: DocumentStatus


class DocumentListItem(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    chunks_count: int
    created_at: datetime


class DocumentDetailResponse(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    chunks_count: int
    file_size: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str
