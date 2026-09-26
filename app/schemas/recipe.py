from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError


class RecipeBase(BaseModel):
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


class RecipeCreate(RecipeBase):
    ingredients: list[str] = Field(
        ...,
        min_length=1,
        description="Ingredients of the recipe(min 1)",
        examples=[["Яйце", "Молоко", "Мука"]]
    )

@field_validator("ingredients")
@classmethod
def validate_ingredients(cls, v: list[str]) -> list[str]:
    cleaned = [name.strip() for name in v if name.strip()]
    if not cleaned:
        raise ValidationError("Ingredients cannot be empty")
    return cleaned

class RecipeUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=150
    )
    description: str | None = Field(
        default=None,
        min_length=1
    )
    prep_time: int | None = Field(
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
        if v is None:
            return None
        cleaned = [name.strip() for name in v if name.strip()]
        if not cleaned:
            raise ValueError("Cant be empty")
        return cleaned

class RecipeResponse(RecipeBase):
    id: int
    ingredients: list[str]

    model_config = ConfigDict(from_attributes=True)
    
    @field_validator("ingredients", mode = "before")
    @classmethod
    def extract_ingredient_name(cls, v: object) -> list[str]:
        if isinstance(v, list):
            return [item.name if hasattr(item, "name") else str(item) for item in v]
        return v