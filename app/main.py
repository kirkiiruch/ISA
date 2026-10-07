from contextlib import asynccontextmanager
from fastapi import FastAPI
import psycopg2
import redis

from app.core.config import settings
from app.core.database import Base, engine
import app.models.weather
from app.api.weather import router as weather_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(
    title="Weather Analytics API",
    lifespan=lifespan,
)

app.include_router(weather_router, prefix="/api/weather", tags=["Weather"])


@app.get("/")
def read_root():
    return {"status": "running"}


@app.get("/health")
def health_check():
    db_status = "connected"
    cache_status = "connected"

    try:
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.POSTGRES_PORT,
            dbname=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            connect_timeout=3
        )
        conn.close()
    except Exception as e:
        db_status = f"error: {e}"

    try:
        r = redis.Redis(host=settings.redis_host, port=settings.REDIS_PORT, socket_timeout=3)
        if not r.ping():
            cache_status = "error: ping failed"
    except Exception as e:
        cache_status = f"error: {e}"

    return {"database": db_status, "cache": cache_status}