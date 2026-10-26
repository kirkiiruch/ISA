"""Репозиторій для роботи з текстовими чанками та векторним пошуком."""

import math
import re
import logging
from typing import List, Optional, Dict, Any
from pymongo.asynchronous.database import AsyncDatabase
from app.models.document import ChunkModel

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "яка", "який", "які", "яке", "якого", "якій", "яким", "яких", "якому", "яку",
    "що", "таке", "такий", "така", "такі", "коли", "де", "хто", "як", "чи", "або",
    "та", "для", "про", "і", "й", "у", "в", "з", "із", "зі", "до", "на", "по", "за", "не",
    "від", "при", "між", "під", "над", "але", "щоб", "цей", "цього", "цій",
    "ця", "це", "ці", "цих", "ті", "той", "те", "тих", "він", "вона",
    "вони", "його", "її", "їх", "ми", "ви", "ти", "вам", "нам", "них", "ним",
    "можна", "треба", "необхідно", "потрібно", "має", "мають", "діє", "діють",
    "робити", "зробити", "виконувати", "бути", "є", "був", "була", "були",
    "напиши", "напишіть", "скажи", "скажіть", "розкажи", "розкажіть", "поясни", "поясніть",
    "скільки", "чому", "куди", "звідки", "через", "після",
    "перед", "якщо", "тоді", "лише", "тільки", "також", "всі", "усі", "усіх",
    "кожен", "кожна", "кожного", "компанії", "компанія", "співробітник",
    "співробітника", "співробітнику", "роботи", "робочий", "день", "дні", "днів",
    "процедура", "правило", "правила", "інформація", "документ", "документах",
    "знаходиться", "розташований", "надається", "нараховується", "отримати",
    "какой", "какая", "какие", "какое", "какого", "каком", "что", "такое",
    "когда", "где", "кто", "как", "или", "প্র", "при", "между", "под",
    "над", "этот", "эта", "это", "эти", "этого", "можно", "нужно", "надо",
    "делать", "сделать", "скажи", "расскажи", "сколько", "почему",
    "если", "только", "также", "все", "каждый", "компании",
    "сотрудник", "сотрудника", "работы", "рабочий",
    "what", "when", "where", "who", "how", "which", "why", "the", "and",
    "for", "with", "from", "that", "this", "are", "was", "were", "can",
    "write", "example", "company",
}


def _word_stem(word: str) -> str:
    """Отримання основи слова для зіставлення морфологічних форм."""
    n = len(word)
    if n <= 3:
        return word
    if n <= 5:
        return word[: n - 1]
    if n <= 7:
        return word[: n - 2]
    return word[: max(4, n - 3)]


def _tokenize_words(text: str) -> List[str]:
    """Розбиття тексту на окремі слова в нижньому регістрі."""
    return re.findall(r"[a-zа-яіїєґ0-9]+", text.lower())


def _extract_query_stems(query_text: str) -> List[str]:
    """Виділення основ ключових слів із запитання користувача."""
    tokens = _tokenize_words(query_text)
    keywords = [
        t for t in tokens
        if t not in STOP_WORDS and (len(t) >= 3 or any(ch.isdigit() for ch in t))
    ]
    if not keywords:
        keywords = [t for t in tokens if len(t) >= 2]
    stems: List[str] = []
    for kw in keywords:
        st = _word_stem(kw)
        if st not in stems:
            stems.append(st)
    return stems


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Обчислення нормалізованого косинусного сходства двох векторів."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    cos = dot / (norm1 * norm2)
    return (cos + 1.0) / 2.0


class ChunkRepository:
    """Клас доступу до чанків та векторного індексу."""

    def __init__(self, db: AsyncDatabase):
        self.collection = db["chunks"]

    async def insert_many(self, chunks: List[ChunkModel]) -> int:
        """Зберегти список чанків у базу."""
        if not chunks:
            return 0
        docs = [chunk.model_dump() for chunk in chunks]
        result = await self.collection.insert_many(docs)
        return len(result.inserted_ids)

    async def delete_by_document_id(self, doc_id: str) -> int:
        """Видалити всі чанки конкретного документа."""
        result = await self.collection.delete_many({"document_id": doc_id})
        return result.deleted_count

    async def get_by_document_id(self, doc_id: str) -> List[ChunkModel]:
        """Отримати всі чанки документа за порядком індексів."""
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
        query_text: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Векторний пошук у MongoDB Atlas з гібридним лексичним реранкінгом та fallback."""
        if query_text:
            all_candidates = await self._fallback_vector_search(
                query_embedding, document_ids, top_k=1000
            )
            return self._rerank_with_lexical(all_candidates, query_text, top_k)

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
            res = self.collection.aggregate(pipeline)
            cursor = await res if hasattr(res, "__await__") else res
            results = []
            async for doc in cursor:
                results.append(doc)
            if results:
                return results
        except Exception as e:
            logger.info("Atlas Search недоступний (%s), застосовується косинусний fallback", e)
        return await self._fallback_vector_search(query_embedding, document_ids, top_k)

    def _rerank_with_lexical(
        self,
        candidates: List[Dict[str, Any]],
        query_text: str,
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Гібридне ранжування чанків з урахуванням ключових слів запиту та IDF."""
        if not candidates:
            return []

        stems = _extract_query_stems(query_text)
        if not stems:
            return candidates[:top_k]

        chunk_words_list = [
            _tokenize_words(c.get("text", ""))
            for c in candidates
        ]

        # Перевірка наявності технічних латинських термінів із запиту в базі
        latin_stems = [st for st in stems if re.match(r"^[a-z0-9]+$", st)]
        for lst in latin_stems:
            if not any(any(w.startswith(lst) for w in cw) for cw in chunk_words_list):
                for c in candidates:
                    c["score"] = round(float(c.get("score", 0.0)) * 0.3, 4)
                return candidates[:top_k]

        # Документна частота (df) кожної основи серед чанків
        df: Dict[str, int] = {}
        for st in stems:
            df[st] = sum(
                1 for cw in chunk_words_list if any(w.startswith(st) for w in cw)
            )

        matched_stems_in_db = [st for st in stems if df[st] > 0]
        doc_coverage = len(matched_stems_in_db) / len(stems)

        # Якщо половина або більше ключових понять запиту взагалі відсутні в базі
        if len(stems) >= 2 and doc_coverage <= 0.50:
            for c in candidates:
                c["score"] = round(float(c.get("score", 0.0)) * 0.35, 4)
            return candidates[:top_k]
        if len(stems) == 1 and doc_coverage == 0.0:
            for c in candidates:
                c["score"] = round(float(c.get("score", 0.0)) * 0.35, 4)
            return candidates[:top_k]

        # IDF-ваги для знайдених основ
        weights = {st: 1.0 / (1.0 + math.log(df[st])) for st in matched_stems_in_db}
        total_weight = sum(weights.values()) or 1.0

        for idx, c in enumerate(candidates):
            vec_score = float(c.get("score", 0.0))
            cw = chunk_words_list[idx]
            matched_w = sum(
                weights[st] for st in matched_stems_in_db if any(w.startswith(st) for w in cw)
            )
            overlap_ratio = matched_w / total_weight
            if overlap_ratio < 0.18:
                c["score"] = round(vec_score * 0.4, 4)
            else:
                c["score"] = round(min(0.99, 0.55 + 0.35 * overlap_ratio + 0.10 * vec_score), 4)

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    async def _fallback_vector_search(
        self,
        query_embedding: List[float],
        document_ids: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Резервний пошук найбільш схожих чанків за косинусною відстанню."""
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
