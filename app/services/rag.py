"""RAG-сервіс для формування контексту та генерації відповідей."""

import json
import logging
from typing import AsyncGenerator, List, Optional, Dict, Any
from app.ai.base import LLMClient
from app.schemas.rag import AskRequest, AskResponse, SourceItem
from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "У документах не знайдено інформації за цим запитом"

SYSTEM_PROMPT = (
    "Ви — помічник з корпоративної бази знань. "
    "Відповідайте на запитання користувача ВИКЛЮЧНО на основі наданого нижче контексту документів. "
    "Вам суворо заборонено використовувати власні знання, домислювати факти чи відповідати на те, чого немає в контексті. "
    "Якщо наданого контексту недостатньо або інформація відсутня, відповідайте: 'У документах не знайдено інформації за цим запитом'."
)


def build_context_prompt(chunks: List[Dict[str, Any]], question: str) -> str:
    """Побудова підсумкового текстового промпту з контекстом знайдених документів."""
    context_parts = []
    for chunk in chunks:
        fn = chunk.get("filename", "unknown")
        page = chunk.get("page")
        page_info = f", Сторінка: {page}" if page else ""
        text = chunk.get("text", "").strip()
        context_parts.append(f"[Документ: {fn}{page_info}]\n{text}")

    full_context = "\n\n---\n\n".join(context_parts)
    return f"Контекст документів:\n{full_context}\n\nЗапитання: {question}\nВідповідь:"


class RAGService:
    """Сервіс відповіді на питання на базі внутрішніх документів."""

    def __init__(self, retrieval_service: RetrievalService, llm_client: LLMClient):
        self.retrieval_service = retrieval_service
        self.llm_client = llm_client

    async def ask(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> AskResponse:
        """Звичайна генерація відповіді без стримінгу."""
        chunks, sources = await self.retrieval_service.retrieve(
            question=question,
            document_ids=document_ids,
            top_k=top_k,
        )

        if not chunks:
            return AskResponse(answer=NOT_FOUND_MESSAGE, sources=[])

        prompt = build_context_prompt(chunks, question)
        answer = await self.llm_client.generate(prompt=prompt, system_prompt=SYSTEM_PROMPT)
        return AskResponse(answer=answer, sources=sources)

    async def ask_stream(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """Потокова віддача відповіді через події SSE."""
        try:
            chunks, sources = await self.retrieval_service.retrieve(
                question=question,
                document_ids=document_ids,
                top_k=top_k,
            )

            # Спочатку відправляємо список знайдених джерел
            sources_json = json.dumps([s.model_dump() for s in sources], ensure_ascii=False)
            yield f"event: sources\ndata: {sources_json}\n\n"

            if not chunks:
                token_json = json.dumps({"text": NOT_FOUND_MESSAGE}, ensure_ascii=False)
                yield f"event: token\ndata: {token_json}\n\n"
                yield "event: done\ndata: {}\n\n"
                return

            prompt = build_context_prompt(chunks, question)

            async for token in self.llm_client.generate_stream(prompt=prompt, system_prompt=SYSTEM_PROMPT):
                token_json = json.dumps({"text": token}, ensure_ascii=False)
                yield f"event: token\ndata: {token_json}\n\n"

            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            logger.error("Помилка під час ask_stream: %s", e)
            err_json = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err_json}\n\n"
