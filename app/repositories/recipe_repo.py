"""Репозиторій для роботи з кулінарними рецептами в базі даних.

Призначення файлу:
Інкапсулює всі операції читання, запису, оновлення та видалення (CRUD),
а також логіку фільтрації та побудови запитів SQLAlchemy 2.0.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.recipe import Ingredient, Recipe
from app.schemas.recipe import RecipeCreate, RecipeUpdate


class RecipeRepository:
    """Клас репозиторію для сутності Recipe.

      Керує транзакціями та виконанням SQL-запитів до таблиць `recipes` та `ingredients`.
      """

    def __init__(self, db: Session):
        """Ініціалізує екземпляр репозиторію з відкритою сесією SQLAlchemy."""
        self.db = db

    def create(self, recipe_in: RecipeCreate) -> Recipe:
        """Створює новий рецепт та прив'язані до нього інгредієнти в одній транзакції.

            Принцип роботи:
            1. Перетворює плаский список рядків `recipe_in.ingredients` на список
            об'єктів Ingredient.
            2. Ініціалізує модель Recipe і передає туди інгредієнти.
            3. Виконує додавання об'єкта, фіксацію змін (.commit) та зчитує присвоєний
            ID (.refresh).
            """
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
        """Знаходить рецепт за первинним ключем ID.

            Особливості:
            - Використовує `selectinload(Recipe.ingredients)`, щоб завантажити всі
              пов'язані інгредієнти за один крок і запобігти помилці DetachedInstanceError.
            - Повертає знайдений об'єкт Recipe або None, якщо запис відсутній.
            """
        stmt = (
            select(Recipe)
            .where(Recipe.id == recipe_id)
            .options(selectinload(Recipe.ingredients))# selectinload (захист вiд проблеми N+1)
        )
        return self.db.scalars(stmt).first()

    def get_all(self, max_prep_time: int | None = None, ingredient: str | None = None) -> list[Recipe]:
        """Повертає каталог рецептів з динамічною фільтрацією за часом та інгредієнтами.

            Логіка фільтрів:
            1. `max_prep_time`: додає умову `prep_time_minutes <= max_prep_time`.
            2. `ingredient`: використовує метод `.any()` та SQL-оператор `ILIKE`
            (регістронезалежний пошук).
               Це дозволяє знайти страву, навіть якщо назва інгредієнта введена не
               повністю або в іншому регістрі.
            """
        stmt = select(Recipe).options(selectinload(Recipe.ingredients))

        # Фільтрація за максимальним часом приготування
        if max_prep_time is not None:
            stmt = stmt.where(Recipe.prep_time_minutes <= max_prep_time)

        # Фільтрація за частковим збігом назви інгредієнта (без урахування регістру)
        if ingredient and ingredient.strip():
            clean_ingredient = ingredient.strip()
            stmt = stmt.where(
                Recipe.ingredients.any(
                    Ingredient.name.ilike(f"%{clean_ingredient}%")
                )
            )
        return list(self.db.scalars(stmt).all())

    def update(self, recipe: Recipe, recipe_in: RecipeUpdate) -> Recipe:
        """Виконує часткове оновлення (PATCH) існуючого запису.

            Принцип роботи:
            1. `model_dump(exclude_unset=True)` вибирає лише ті поля, які клієнт явно
            надіслав у запиті.
            2. Оновлює відповідні скалярні стовпці об'єкта через `setattr`.
            3. Якщо в запиті передано новий список інгредієнтів, старі автоматично
            видаляються
               (завдяки налаштуванню `delete-orphan`), а нові прив'язуються до рецепта.
            """
        # Оновлення базових полів (назва, опис, час приготування)
        update_data = recipe_in.model_dump(
            exclude_unset=True, exclude={"ingredients"}
        )
        for field, value in update_data.items():
            setattr(recipe, field, value)


        # Оновлення інгредієнтів (якщо вони були передані)
        if recipe_in.ingredients is not None:
            recipe.ingredients = [
                Ingredient(name=name) for name in recipe_in.ingredients
            ]
        self.db.commit()
        self.db.refresh(recipe)
        return recipe



    def delete(self, recipe: Recipe) -> None:
        """Видаляє рецепт із бази даних.

            Завдяки налаштуванню каскадного зв'язку на рівні моделі та зовнішнього ключа
            в базі,
            усі пов'язані рядки з таблиці `ingredients` видаляються автоматично.
            """

        self.db.delete(recipe)
        self.db.commit()