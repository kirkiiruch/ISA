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
    summary="Ask a question without streaming",
)
async def ask_question(
    request: AskRequest,
    rag_service: RAGService = Depends(get_rag_service),
):
    return await rag_service.ask(
        question=request.question,
        document_ids=request.document_ids,
        top_k=request.top_k,
    )


@router.get(
    "/stream",
    summary="Ask a question with Server-Sent Events (SSE) streaming",
)
async def ask_question_stream(
    request: Request,
    question: str = Query(..., min_length=3, max_length=1000, description="User question"),
    document_ids: Optional[List[str]] = Query(None, description="Optional document ID filters"),
    top_k: Optional[int] = Query(None, ge=1, le=10, description="Top-K chunks to retrieve"),
    rag_service: RAGService = Depends(get_rag_service),
):
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
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
