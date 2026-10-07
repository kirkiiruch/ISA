import redis
from app.core.config import settings

redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.REDIS_PORT,
    decode_responses=True,
    socket_timeout=3.0,
    socket_connect_timeout=3.0,
)


def get_redis() -> redis.Redis:
    return redis_client


def get_redis_client() -> redis.Redis:
    return redis_client
