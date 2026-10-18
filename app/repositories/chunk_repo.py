import math
import logging
from typing import List, Optional, Dict, Any
from pymongo.asynchronous.database import AsyncDatabase
from app.models.document import ChunkModel

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    cos = dot / (norm1 * norm2)
    # Normalized score like Atlas cosine [0, 1]
    return (cos + 1.0) / 2.0


class ChunkRepository:
    def __init__(self, db: AsyncDatabase):
        self.collection = db["chunks"]

    async def insert_many(self, chunks: List[ChunkModel]) -> int:
        if not chunks:
            return 0
        docs = [chunk.model_dump() for chunk in chunks]
        result = await self.collection.insert_many(docs)
        return len(result.inserted_ids)

    async def delete_by_document_id(self, doc_id: str) -> int:
        result = await self.collection.delete_many({"document_id": doc_id})
        return result.deleted_count

    async def get_by_document_id(self, doc_id: str) -> List[ChunkModel]:
        cursor = self.collection.find({"document_id": doc_id}, {"_id": 0}).sort("chunk_index", 1)
        results = []
        async for doc in cursor:
            results.append(ChunkModel.model_validate(doc))
        return results

    async def vector_search(
        self,
        query_embedding: List[float],
        document_ids: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Executes vector search. Tries MongoDB Atlas $vectorSearch pipeline first,
        falls back to in-memory cosine similarity if Atlas search is unavailable.
        """
        vector_search_stage: Dict[str, Any] = {
            "index": "vector_index",
            "path": "embedding",
            "queryVector": query_embedding,
            "numCandidates": max(top_k * 10, 20),
            "limit": top_k,
        }

        if document_ids:
            if len(document_ids) == 1:
                vector_search_stage["filter"] = {"document_id": document_ids[0]}
            else:
                vector_search_stage["filter"] = {"document_id": {"$in": document_ids}}

        pipeline = [
            {"$vectorSearch": vector_search_stage},
            {
                "$project": {
                    "_id": 0,
                    "id": 1,
                    "document_id": 1,
                    "filename": 1,
                    "chunk_index": 1,
                    "page": 1,
                    "text": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            cursor = self.collection.aggregate(pipeline)
            results = []
            async for doc in cursor:
                results.append(doc)
            return results
        except Exception as e:
            logger.info("Atlas $vectorSearch failed or not supported (%s), using cosine similarity fallback", e)
            return await self._fallback_vector_search(query_embedding, document_ids, top_k)

    async def _fallback_vector_search(
        self,
        query_embedding: List[float],
        document_ids: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        query_filter = {}
        if document_ids:
            if len(document_ids) == 1:
                query_filter["document_id"] = document_ids[0]
            else:
                query_filter["document_id"] = {"$in": document_ids}

        cursor = self.collection.find(query_filter, {"_id": 0})
        scored_chunks = []
        async for doc in cursor:
            emb = doc.get("embedding", [])
            score = cosine_similarity(query_embedding, emb)
            scored_chunks.append({
                "id": doc.get("id"),
                "document_id": doc.get("document_id"),
                "filename": doc.get("filename"),
                "chunk_index": doc.get("chunk_index"),
                "page": doc.get("page"),
                "text": doc.get("text"),
                "score": score,
            })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]
