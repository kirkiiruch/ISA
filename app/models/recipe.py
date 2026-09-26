"""ORM-моделі бази даних для рецептів та інгредієнтів.

Призначення файлу:
Описує структуру таблиць PostgreSQL `recipes` та `ingredients`, типи їх колонок,
первинні та зовнішні ключі, а також логічні зв'язки між ними
за стандартом SQLAlchemy 2.0.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Recipe(Base):
  """Модель кулінарного рецепта (головна таблиця `recipes`).

  Зберігає ключову інформацію про страву: назву, опис, тривалість приготування,
  а також має реляційний зв'язок зі списком її інгредієнтів.
  """

  __tablename__ = "recipes"

  # Первинний ключ з автоматичною автоінкрементацією в PostgreSQL
  id: Mapped[int] = mapped_column(
      primary_key=True
  )
  # Назва страви (індексується для прискорення пошукових запитів)
  title: Mapped[str] = mapped_column(
      String(150),
      nullable=False,
      index=True
  )
  # Детальний текстовий опис процесу приготування
  description: Mapped[str] = mapped_column(
      Text,
      nullable=False
  )
  # Час приготування в хвилинах (використовується для числової фільтрації)
  prep_time_minutes: Mapped[int] = mapped_column(
      nullable=False,
      index=True
  )

  # Зв'язок One-to-Many: один рецепт має багато інгредієнтів.
  # - cascade="all, delete-orphan": видаляє пов'язані інгредієнти з бази,
  #   якщо рецепт видалено або інгредієнт вилучено зі списку.
  # - passive_deletes=True: оптимізація, яка повідомляє SQLAlchemy покластися
  #   на CASCADE-обмеження самої СУБД PostgreSQL.
  ingredients: Mapped[list[Ingredient]] = relationship(
      back_populates="recipe",
      cascade="all, delete-orphan",
      passive_deletes=True,
  )


class Ingredient(Base):
  """Модель інгредієнта (підпорядкована таблиця `ingredients`).

  Зберігає назву окремого інгредієнта та зовнішній ключ,
  який прив'язує його до конкретного рецепта."""
  __tablename__ = "ingredients"

  # Первинний ключ інгредієнта
  id: Mapped[int] = mapped_column(
      primary_key=True
  )

  # Назва інгредієнта (наприклад, "Яйце", "Сир")
  name: Mapped[str] = mapped_column(
      String(100),
      nullable=False,
      index=True

  )

  # Зовнішній ключ (Foreign Key) на таблицю recipes.
  # ondelete="CASCADE" на рівні PostgreSQL гарантує фізичне видалення рядка,
  # якщо батьківський рецепт з таким ID було видалено.
  recipe_id: Mapped[int] = mapped_column(
      ForeignKey("recipes.id", ondelete="CASCADE"),
      nullable=False
  )

  # Зворотний зв'язок (Many-to-One): посилання на батьківський об'єкт Recipe
  recipe: Mapped[Recipe] = relationship(
      back_populates="ingredients"
  )