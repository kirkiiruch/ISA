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
    "Ви — точний асистент корпоративної бази знань. "
    "Ви відповідаєте на запитання користувача ВИКЛЮЧНО на основі наданих фрагментів документів. "
    "Заборонено вигадувати факти, генерувати програмний код або підміняти поняття іншими розділами документа. "
    "Якщо у фрагментах документів взагалі немає інформації за темою запитання, поверніть рівно одну фразу: "
    "У документах не знайдено інформації за цим запитом"
)


def build_context_prompt(chunks: List[Dict[str, Any]], question: str) -> str:
    """Побудова підсумкового текстового промпту з контекстом знайдених документів."""
    context_parts = []
    for chunk in chunks:
        text = chunk.get("text", "").strip()
        if text:
            context_parts.append(text)

    full_context = "\n\n---\n\n".join(context_parts)
    return (
        f"Фрагменти документів:\n{full_context}\n\n"
        f"Запитання користувача: {question}\n\n"
        "Проаналізуй фрагменти документів вище:\n"
        "- Якщо у фрагментах є інформація щодо запитання, випиши всі релевантні факти, точні цифри, суми, коди, паролі, ліміти та правила з тексту і дай пряму та повну відповідь на кожну частину запитання.\n"
        "- Якщо ж у фрагментах взагалі немає інформації про те, що запитується, виведи лише: У документах не знайдено інформації за цим запитом"
    )


def _is_not_found_answer(answer: str) -> bool:
    """Перевірка, чи є відповідь моделі повідомленням про відсутність інформації."""
    cleaned = answer.strip().rstrip(".")
    if cleaned == NOT_FOUND_MESSAGE:
        return True
    if NOT_FOUND_MESSAGE in cleaned and len(cleaned) < len(NOT_FOUND_MESSAGE) + 35:
        return True
    return False


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
        if _is_not_found_answer(answer):
            return AskResponse(answer=NOT_FOUND_MESSAGE, sources=[])
        return AskResponse(answer=answer.strip(), sources=sources)

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
