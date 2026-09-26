from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.recipe import Ingredient, Recipe
from app.schemas.recipe import RecipeCreate, RecipeUpdate


class RecipeRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, recipe_in: RecipeCreate) -> Recipe:
        db_ingridients = [Ingredient(name=name) for name in recipe_in.ingredients]

        db_recipe = Recipe(
            title = recipe_in.title,
            description = recipe_in.description,
            prep_time_minutes = recipe_in.prep_time_minutes,
            ingredients = db_ingridients,
        )

        self.db.add(db_recipe)
        self.db.commit()
        self.db.refresh(db_recipe)
        return db_recipe

    def get_by_id(self, recipe_id: int) -> Recipe | None:
        stmt = (
            select(Recipe)
            .where(Recipe.id == recipe_id)
            .options(selectinload(Recipe.ingredients))# selectinload (захист вiд проблеми N+1)
        )
        return self.db.scalar(stmt).first()

    def get_all(self, max_prep_time: int | None = None, ingredient: str | None = None) -> list[Recipe]:
        stmt = select(Recipe).options(selectinload(Recipe.ingredients))

        if max_prep_time is not None:
            stmt = stmt.where(Recipe.prep_time_minutes <= max_prep_time)

        if ingredient and ingredient.strip():
            clean_ingredient = ingredient.strip()
            stmt = stmt.where(
                Recipe.ingredients.any(
                    Ingredient.name.ilike(f"%{clean_ingredient}%")
                )
            )
        return list(self.db.scalars(stmt).all())

    def update(self, recipe: Recipe, recipe_in: RecipeUpdate) -> Recipe:
        update_data = recipe_in.model_dump(
            exclude_unset=True, exclude={"ingredients"}
        )
        for field, value in update_data.items():
            setattr(recipe, field, value)

        if recipe_in.ingredients is not None:
            recipe.ingredients = [
                Ingredient(name=name) for name in recipe_in.ingredients
            ]
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def delete(self, recipe: Recipe) -> None:
        self.db.delete(recipe)
        self.db.commit()