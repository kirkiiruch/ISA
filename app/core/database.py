import logging
from typing import Optional
from pymongo import AsyncMongoClient, ASCENDING
from pymongo.asynchronous.database import AsyncDatabase
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_mongo_client: Optional[AsyncMongoClient] = None


def get_mongo_client(settings: Optional[Settings] = None) -> AsyncMongoClient:
    global _mongo_client
    if _mongo_client is None:
        cfg = settings or get_settings()
        _mongo_client = AsyncMongoClient(cfg.MONGODB_URL)
    return _mongo_client


async def close_mongo_client():
    global _mongo_client
    if _mongo_client is not None:
        await _mongo_client.close()
        _mongo_client = None


def get_db(settings: Optional[Settings] = None) -> AsyncDatabase:
    cfg = settings or get_settings()
    client = get_mongo_client(cfg)
    return client[cfg.MONGODB_DB_NAME]


async def init_indexes(db: AsyncDatabase):
    """
    Creates necessary regular and vector search indexes on collections.
    """
    try:
        # Documents collection indexes
        docs_col = db["documents"]
        await docs_col.create_index([("id", ASCENDING)], unique=True)
        await docs_col.create_index([("content_hash", ASCENDING)], unique=True)
        await docs_col.create_index([("created_at", ASCENDING)])
        logger.info("Created indexes on 'documents' collection")

        # Chunks collection indexes
        chunks_col = db["chunks"]
        await chunks_col.create_index([("id", ASCENDING)], unique=True)
        await chunks_col.create_index([("document_id", ASCENDING)])
        logger.info("Created indexes on 'chunks' collection")

        try:
            vector_index_spec = {
                "name": "vector_index",
                "type": "vectorSearch",
                "definition": {
                    "fields": [
                        {
                            "type": "vector",
                            "path": "embedding",
                            "numDimensions": 768,
                            "similarity": "cosine",
                        },
                        {
                            "type": "filter",
                            "path": "document_id",
                        },
                    ]
                },
            }
            if hasattr(chunks_col, "create_search_index"):
                existing = []
                try:
                    res = chunks_col.list_search_indexes()
                    cursor = await res if hasattr(res, "__await__") else res
                    async for idx in cursor:
                        existing.append(idx.get("name"))
                except Exception:
                    pass

                if "vector_index" not in existing:
                    await chunks_col.create_search_index(model=vector_index_spec)
        except Exception as e:
            logger.info("Search index note: %s", e)

    except Exception as e:
        logger.error("Error during database index initialization: %s", e)
        raise
