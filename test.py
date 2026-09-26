from app.core.database import Base, SessionLocal, engine
from app.models.recipe import Ingredient, Recipe

# 1. Заставляем SQLAlchemy создать таблицы в Postgres
print("Создаем таблицы в базе данных...")
Base.metadata.create_all(bind=engine)
print("Таблицы успешно созданы!")

# 2. Открываем сессию
db = SessionLocal()

# 3. Вставляем тестовую запись
new_recipe = Recipe(
    title="Омлет",
    description="Взбейте яйца с молоком и обжарьте на сковороде.",
    prep_time_minutes=10,
    ingredients=[Ingredient(name="Яйцо"), Ingredient(name="Молоко")],
)
db.add(new_recipe)
db.commit()
print(f"Рецепт успешно сохранен! ID: {new_recipe.id}")

# 4. Читаем из базы
saved_recipe = db.query(Recipe).filter_by(title="Омлет").first()
print(
    f"Ингредиенты из базы: {[ing.name for ing in saved_recipe.ingredients]}"
)

# 5. Удаляем тестовую запись
db.delete(saved_recipe)
db.commit()
print("Тестовые данные успешно удалены.")

db.close()

from app.models.recipe import Ingredient, Recipe
from app.schemas.recipe import RecipeCreate, RecipeResponse

# 1. Проверяем валидацию входящих данных:
try:
  bad_data = RecipeCreate(
      title="Чай",
      description="Залить кипятком",
      prep_time_minutes=-5,  # Ошибка: меньше нуля
      ingredients=["чай"],
  )
except Exception as e:
  print("Валидация успешно поймала отрицательное время!")

# 2. Проверяем сериализацию ORM-модели в ответ API:
fake_orm_recipe = Recipe(
    id=42,
    title="Омлет",
    description="Обжарить на сковороде",
    prep_time_minutes=10,
    ingredients=[Ingredient(name="Яйцо"), Ingredient(name="Сыр")],
)

response_dto = RecipeResponse.model_validate(fake_orm_recipe)
print("\nУспешная трансформация ORM в JSON-схему:")
print(response_dto.model_dump())