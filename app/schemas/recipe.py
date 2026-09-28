"""Схеми валідації та серіалізації даних (Pydantic DTO).

Призначення файлу:
Визначає контракти вхідних та вихідних даних для REST API.
Забезпечує сувору типізацію, автоматичну санітизацію рядків,
перевірку числових діапазонів і трансформацію складних ORM-моделей
у формат JSON для клієнта.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError

# -------------------------------------------------------------------------
# Базова схема із загальними атрибутами
# -------------------------------------------------------------------------

class RecipeBase(BaseModel):
    """Базова схема рецепта.

  Містить поля, спільні як для створення запису, так і для відображення у відповіді.
  """
    title: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Name of the recipe"
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Description of the recipe"
    )
    prep_time_minutes: int = Field(...,
                             gt=0,
                             description="Prep time of the recipe")


# -------------------------------------------------------------------------
# Схема для створення нового рецепта (POST)
# -------------------------------------------------------------------------
class RecipeCreate(RecipeBase):
    """Вхідний DTO для створення нового рецепта.

      Розширює RecipeBase обов'язковим списком інгредієнтів.
      Не містить поля id, оскільки воно генерується сервером.
      """
    ingredients: list[str] = Field(
        ...,
        min_length=1,
        description="Ingredients of the recipe(min 1)",
        examples=[["Яйце", "Молоко", "Мука"]]
    )

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients(cls, v: list[str]) -> list[str]:
        """Валідатор очищення списку інгредієнтів.

            Призначення:
            - Обрізає випадкові пробіли на початку та в кінці кожного рядка.
            - Видаляє порожні рядки зі списку.
            - Викидає виняток ValueError (статус 422), якщо після очищення список
            виявився порожнім.
            """
        cleaned = [name.strip() for name in v if name.strip()]
        if not cleaned:
            raise ValidationError("Ingredients cannot be empty")
        return cleaned


# -------------------------------------------------------------------------
# Схема для часткового оновлення (PATCH)
# -------------------------------------------------------------------------
class RecipeUpdate(BaseModel):
    """Вхідний DTO для часткової зміни даних рецепта.

      Усі поля є необов'язковими (None за замовчуванням), що дозволяє клієнту
      надсилати для оновлення лише окремі потрібні поля.
      """
    model_config = ConfigDict(extra="forbid")# Забороняє надсилати невідомі поля (наприклад, помилкове prep_time)

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=150
    )
    description: str | None = Field(
        default=None,
        min_length=1
    )
    prep_time_minutes: int | None = Field(
        default=None,
        gt=0
    )
    ingredients: list[str] | None = Field(
        default=None,
        min_length=1
    )

    @field_validator("ingredients")
    @classmethod
    def validate_ingredients(
            cls, v: list[str] | None
    ) -> list[str] | None:
        """Перевіряє коректність інгредієнтів при PATCH-запиті.

            Якщо поле не передано (None), воно ігнорується. Якщо передано — перевіряється,
            щоб у ньому не було суцільних пробілів.
            """
        if v is None:
            return None
        cleaned = [name.strip() for name in v if name.strip()]
        if not cleaned:
            raise ValueError("Cant be empty")
        return cleaned


# -------------------------------------------------------------------------
# Схема для відповіді клієнту (GET, POST, PATCH)
# -------------------------------------------------------------------------
class RecipeResponse(RecipeBase):
    """Вихідний DTO, що повертається клієнту у відповіді API.

      Включає згенерований первинний ключ id та відформатований список інгредієнтів.
      """
    id: int
    ingredients: list[str]

    # from_attributes=True дозволяє Pydantic читати дані напряму з ORM-моделей SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

    @field_validator("ingredients", mode = "before")
    @classmethod
    def extract_ingredient_name(cls, v: object) -> list[str]:
        """Трансформація зв'язаних моделей Ingredient у плоский список рядків.

            Параметр mode='before' перехоплює об'єкти до початку стандартної валідації.
            Якщо на вхід приходить список ORM-об'єктів Ingredient із бази даних,
            метод витягує з кожного з них лише текстове поле `item.name`.
            """
        if isinstance(v, list):
            return [item.name if hasattr(item, "name") else str(item) for item in v]
        return v