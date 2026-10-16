from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content_hash: str
    status: DocumentStatus = DocumentStatus.PROCESSING
    chunks_count: int = 0
    error_message: Optional[str] = None
    file_size: int = 0
    created_at: datetime = Field(default_factory=get_utc_now)
    updated_at: datetime = Field(default_factory=get_utc_now)


class ChunkModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    filename: str
    chunk_index: int
    page: Optional[int] = None
    text: str
    embedding: List[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=get_utc_now)
