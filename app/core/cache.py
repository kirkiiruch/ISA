import json
from typing import Any, Optional
from app.core.config import settings
from app.core.redis import get_redis


class CacheService:
    def __init__(self, client=None):
        self.client = client or get_redis()

    def get(self, key: str) -> Optional[Any]:
        try:
            val = self.client.get(key)
            return json.loads(val) if val else None
        except Exception:
            return None

    def set(self, key: str, value: Any, expire: int = settings.CACHE_EXPIRE) -> None:
        try:
            self.client.set(key, json.dumps(value, default=str), ex=expire)
        except Exception:
            pass

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception:
            pass

    def clear_pattern(self, pattern: str = "weather:*") -> None:
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
        except Exception:
            pass


def get_cache_service() -> CacheService:
    return CacheService()
