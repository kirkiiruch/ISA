"""Модуль залежностей (Dependency Injection) для API.

Призначення файлу:
Забезпечує створення та передачу готових сервісів та репозиторіїв
у функції-контролери (роутери) через механізм FastAPI `Depends()`.
Це запобігає прямому імпорту глобальних змінних та сесій БД у шар презентації.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.recipe_repo import RecipeRepository


def get_recipe_repo(db: Session = Depends(get_db)) -> RecipeRepository:
  """Фабрика для створення екземпляра RecipeRepository.

    Призначення:
    1. Автоматично викликає генератор `get_db()`, який бере робочу сесію з пулу
    SQLAlchemy.
    2. Передає відкриту сесію `db` у конструктор репозиторію.
    3. Гарантує, що після обробки запиту сесія бази даних буде коректно закрита.

    Повертає:
        RecipeRepository: готовий об'єкт репозиторію для доступу до бази даних.
    """
  return RecipeRepository(db=db)