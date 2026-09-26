from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.recipes import router as recipes_router
from app.core.database import Base, engine
import app.models.recipe


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Асинхронний менеджер життєвого циклу додатку.

  Принцип роботи:
  1. Код ДО оператора `yield` виконується ОДИН РАЗ при старті сервера Uvicorn:
     - `create_all()` перевіряє наявність таблиць `recipes` та `ingredients` у PostgreSQL
       і створює їх, якщо база щойно розгорнута.
  2. Оператор `yield` передає керування додатку — сервер починає приймати HTTP-запити.
  3. Код ПІСЛЯ `yield` спрацьовує при коректному вимкненні контейнера (Graceful Shutdown):
     - `engine.dispose()` закриває всі відкриті TCP-з'єднання з базою даних,
       запобігаючи витоку ресурсів.
       """
  Base.metadata.create_all(bind=engine)
  yield
  engine.dispose()


app = FastAPI(
    title="Recipe Management API",
    version="1.0.0",
    description="REST API для управління кулінарними рецептами та інгрідіентами",
    lifespan=lifespan,
)

app.include_router(recipes_router)


@app.get("/", tags=["System"])
def root():
  return {
    "status": "running",
    "docs_url": "/docs",
    "message": "Recipe Management API is healthy and operational",
  }