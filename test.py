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