from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Recipe(Base):
  __tablename__ = "recipes"

  id: Mapped[int] = mapped_column(
      primary_key=True
  )

  title: Mapped[str] = mapped_column(
      String(150),
      nullable=False,
      index=True
  )

  description: Mapped[str] = mapped_column(
      Text,
      nullable=False
  )

  prep_time_minutes: Mapped[int] = mapped_column(
      nullable=False,
      index=True
  )


  ingredients: Mapped[list[Ingredient]] = relationship(
      back_populates="recipe",
      cascade="all, delete-orphan",
      passive_deletes=True,
  )


class Ingredient(Base):
  __tablename__ = "ingredients"

  id: Mapped[int] = mapped_column(
      primary_key=True
  )

  name: Mapped[str] = mapped_column(
      String(100),
      nullable=False,
      index=True

  )
  recipe_id: Mapped[int] = mapped_column(
      ForeignKey("recipes.id", ondelete="CASCADE"),
      nullable=False
  )

  recipe: Mapped[Recipe] = relationship(
      back_populates="ingredients"
  )