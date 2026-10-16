from typing import List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="User question to knowledge base")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional document IDs filter")
    top_k: Optional[int] = Field(default=None, ge=1, le=10, description="Number of top chunks to retrieve")


class SourceItem(BaseModel):
    document_id: str
    filename: str
    page: Optional[int] = None
    score: float
    snippet: str


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


class TokenEvent(BaseModel):
    text: str


class ErrorEvent(BaseModel):
    error: str
