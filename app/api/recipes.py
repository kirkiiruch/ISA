"""Контролери (роутери) для роботи з кулінарними рецептами.

Призначення файлу:
Оголошує маршрути (endpoints) REST API, обробляє вхідні HTTP-запити,
задає моделі відповідей, коди статусів помилок і успішних дій,
а також передає виконання операцій у шар RecipeRepository.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_recipe_repo
from app.repositories.recipe_repo import RecipeRepository
from app.schemas.recipe import RecipeCreate, RecipeResponse, RecipeUpdate

router = APIRouter()

# -------------------------------------------------------------------------
# Створення рецепта
# -------------------------------------------------------------------------
@router.post(
    "/api/recipes",
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new recipe",
)
def create_recipe(
    recipe_in: RecipeCreate,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
  """Ендпоінт для створення нового рецепта з інгредієнтами.
    Призначення:
      - Приймає валідовані вхідні дані через DTO-схему `RecipeCreate`.
      - Викликає метод `repo.create()`, який створює рецепт і прив'язані
      інгредієнти.
      - Повертає статус 201 Created та повну схему рецепта із присвоєним ID.
      """
  return repo.create(recipe_in=recipe_in)


# -------------------------------------------------------------------------
# Отримання списку рецептів із фільтрацією
# -------------------------------------------------------------------------
@router.get(
    "/api/recipes",
    response_model=list[RecipeResponse],
    status_code=status.HTTP_200_OK,
    summary="Get list recipes with filtres",
)
def get_recipes(
    max_prep_time: int | None = Query(
        default=None, gt=0, description="Max coocking time"
    ),
    ingredient: str | None = Query(
        default=None, min_length=1, description="Ingredient name"
    ),
    repo: RecipeRepository = Depends(get_recipe_repo),
):
  """Ендпоінт для отримання каталогу рецептів.

      Призначення:
      - Приймає опціональні query-параметри для фільтрації: `max_prep_time` та
      `ingredient`.
      - Делегує виконання SQL-фільтрації репозиторію.
      - Повертає список рецептів (або порожній список [], якщо збігів не знайдено).
      """
  return repo.get_all(max_prep_time=max_prep_time, ingredient=ingredient)



# -------------------------------------------------------------------------
# Отримання одного рецепта за ID
# -------------------------------------------------------------------------
@router.get(
    "/api/v1/recipes/{recipe_id}",
    response_model=RecipeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full info about a recipe",
)
def get_recipe_by_id(
    recipe_id: int, repo: RecipeRepository = Depends(get_recipe_repo)
):
  """Ендпоінт для отримання детальної інформації про конкретний рецепт.

      Призначення:
      - Шукає запис у базі через `repo.get_by_id()`.
      - Якщо рецепт відсутній, перериває запит і викидає виняток 404 Not Found.
      - При успіху повертає об'єкт рецепта разом з усіма зв'язаними інгредієнтами.
      """
  recipe = repo.get_by_id(recipe_id=recipe_id)
  if not recipe:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Рецепт з {recipe_id} не знайдено",
    )
  return recipe



# -------------------------------------------------------------------------
# Часткове оновлення рецепта
# -------------------------------------------------------------------------
@router.patch(
    "/api/v1/recipes/{recipe_id}",
    response_model=RecipeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update data recipe",
)
def update_recipe(
    recipe_id: int,
    recipe_in: RecipeUpdate,
    repo: RecipeRepository = Depends(get_recipe_repo),
):
  """Ендпоінт для модифікації обраних полів рецепта (PATCH).

      Призначення:
      - Перевіряє наявність рецепта за ID (якщо немає — повертає 404).
      - Приймає схему `RecipeUpdate`, де всі поля необов'язкові.
      - Оновлює лише ті поля, які були явно передані клієнтом (включаючи повну
      заміну списку інгредієнтів, якщо вони вказані).
      """
  recipe = repo.get_by_id(recipe_id=recipe_id)
  if not recipe:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Recipe with ID {recipe_id} not found",
    )
  return repo.update(recipe=recipe, recipe_in=recipe_in)



# -------------------------------------------------------------------------
# Видалення рецепта
# -------------------------------------------------------------------------

@router.delete(
    "/api/v1/recipes/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recipe",
)
def delete_recipe(
    recipe_id: int, repo: RecipeRepository = Depends(get_recipe_repo)
):
  """Ендпоінт для видалення рецепта.

      Призначення:
      - Знаходить запис у базі даних (якщо немає — повертає 404).
      - Видаляє рецепт. Завдяки налаштуванню ON DELETE CASCADE у моделі,
        усі зв'язані інгредієнти автоматично видаляються з таблиці `ingredients`.
      - Повертає статус 204 No Content без тіла відповіді згідно зі стандартом REST.
      """
  recipe = repo.get_by_id(recipe_id=recipe_id)
  if not recipe:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Recipe with ID {recipe_id} not found",
    )
  repo.delete(recipe=recipe)
  return None
