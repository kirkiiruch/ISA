"""Головна точка входу сервісу корпоративної бази знань."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routers import documents, ask
from app.core.config import get_settings
from app.core.database import get_db, init_indexes, close_mongo_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ініціалізація підключення до MongoDB та індексів під час старту."""
    try:
        db = get_db()
        await init_indexes(db)
    except Exception as e:
        print(f"Попередження: не вдалося ініціалізувати індекси: {e}")

    yield

    await close_mongo_client()


app = FastAPI(
    title="Corporate Knowledge Base RAG Service",
    version="1.0.0",
    description="RAG-сервіс для пошуку та генерації відповідей за корпоративними документами.",
    lifespan=lifespan,
)

settings = get_settings()

# Підключення статичних файлів інтерфейсу
static_path = os.path.abspath(settings.STATIC_DIR)
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", include_in_schema=False)
async def read_index():
    """Головна сторінка веб-інтерфейсу."""
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Corporate Knowledge Base RAG API is running"}


@app.get("/health", tags=["system"])
async def health_check():
    """Перевірка працездатності сервісу та зв'язку з базою."""
    db_status = "unknown"
    try:
        db = get_db()
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
    }


# Реєстрація роутерів API
app.include_router(documents.router)
app.include_router(ask.router)
