"""Роутер для обробки запитань до бази знань."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_rag_service
from app.schemas.rag import AskRequest, AskResponse
from app.services.rag import RAGService

router = APIRouter(prefix="/api/ask", tags=["ask"])


@router.post(
    "",
    response_model=AskResponse,
    summary="Задати запитання без стримінгу",
)
async def ask_question(
    request: AskRequest,
    rag_service: RAGService = Depends(get_rag_service),
):
    """Отримати повну відповідь та список знайдених джерел."""
    return await rag_service.ask(
        question=request.question,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )


@router.get(
    "/stream",
    summary="Задати запитання у режимі SSE-стримінгу",
)
async def ask_question_stream(
    request: Request,
    question: str = Query(..., min_length=3, max_length=1000, description="Запитання користувача"),
    document_ids: Optional[List[str]] = Query(None, description="Фільтр за списком ID документів"),
    top_k: Optional[int] = Query(None, ge=1, le=10, description="Кількість чанків для пошуку"),
    rag_service: RAGService = Depends(get_rag_service),
):
    """Потокова передача відповіді через text/event-stream."""
    async def sse_generator():
        async for chunk in rag_service.ask_stream(
            question=question,
            document_ids=document_ids,
            top_k=top_k,
        ):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Connection": "close",
            "X-Accel-Buffering": "no",
        },
    )
