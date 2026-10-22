import logging
from typing import List, Optional, Tuple, Dict, Any
from app.ai.base import EmbeddingClient
from app.core.config import Settings
from app.repositories.chunk_repo import ChunkRepository
from app.schemas.rag import SourceItem

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        chunk_repo: ChunkRepository,
        embedding_client: EmbeddingClient,
        settings: Settings,
    ):
        self.chunk_repo = chunk_repo
        self.embedding_client = embedding_client
        self.settings = settings

    async def retrieve(
        self,
        question: str,
        document_ids: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], List[SourceItem]]:
        """
        Retrieves relevant chunks and converts them to SourceItem models.
        Filters out any chunks whose score is below SCORE_THRESHOLD.
        Returns (relevant_raw_chunks, sources).
        """
        effective_top_k = top_k if top_k is not None else self.settings.TOP_K
        threshold = self.settings.SCORE_THRESHOLD

        logger.info("Generating embedding for question: '%s'", question[:50])
        query_embedding = await self.embedding_client.get_embedding(question)

        raw_results = await self.chunk_repo.vector_search(
            query_embedding=query_embedding,
            document_ids=document_ids,
            top_k=effective_top_k,
        )

        relevant_chunks: List[Dict[str, Any]] = []
        sources: List[SourceItem] = []

        for doc in raw_results:
            score = float(doc.get("score", 0.0))
            if score >= threshold:
                relevant_chunks.append(doc)
                snippet = doc.get("text", "")
                if len(snippet) > 300:
                    snippet = snippet[:300] + "..."

                sources.append(
                    SourceItem(
                        document_id=doc.get("document_id", ""),
                        filename=doc.get("filename", ""),
                        page=doc.get("page"),
                        score=round(score, 4),
                        snippet=snippet,
                    )
                )
            else:
                logger.info(
                    "Chunk from %s skipped due to low score: %.4f < %.4f",
                    doc.get("filename"),
                    score,
                    threshold,
                )

        return relevant_chunks, sources
