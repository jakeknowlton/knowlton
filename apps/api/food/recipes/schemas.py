"""Pydantic write/read models for the recipes API.

Quantities cross the wire as human strings on writes (``"1 1/2"``, validated via
`parse_quantity`) and as a flattened ``num`` / ``den`` / ``display`` triple on
reads — the read shape the rest of the plan assumes. Building the read models
requires scaling and step rendering, so they are assembled in the service layer
rather than validated straight off ORM rows.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from food.recipes.enums import Course, IngredientCategory, MealType, Unit
from food.recipes.quantities import InvalidQuantityError, parse_quantity

REF_KEY_PATTERN = r"^[a-z0-9_-]+$"


def _ensure_parseable(value: str) -> str:
    """Validate a quantity string, surfacing parse errors as Pydantic 422s."""
    try:
        parse_quantity(value)
    except InvalidQuantityError as exc:
        raise ValueError(str(exc)) from exc
    return value


# --- Catalog reads ----------------------------------------------------------


class IngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_normalized: str
    category: IngredientCategory | None
    is_staple: bool


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_normalized: str


# --- Writes -----------------------------------------------------------------


class RecipeIngredientWrite(BaseModel):
    ref_key: str = Field(pattern=REF_KEY_PATTERN, min_length=1)
    # Exactly one of these identifies the catalog ingredient: a name to
    # get-or-create, or an existing id.
    ingredient: str | None = None
    ingredient_id: int | None = None
    quantity: str | None = None
    unit: Unit | None = None
    preparation: str | None = None
    is_optional: bool = False
    section: str | None = None
    position: int

    @field_validator("quantity")
    @classmethod
    def _validate_quantity(cls, value: str | None) -> str | None:
        return None if value is None else _ensure_parseable(value)

    @model_validator(mode="after")
    def _exactly_one_ingredient_ref(self) -> "RecipeIngredientWrite":
        if (self.ingredient is None) == (self.ingredient_id is None):
            raise ValueError("Provide exactly one of 'ingredient' or 'ingredient_id'")
        return self


class RecipeStepWrite(BaseModel):
    text: str
    position: int
    section: str | None = None


class RecipeCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    prep_time_minutes: int | None = Field(default=None, ge=0)
    cook_time_minutes: int | None = Field(default=None, ge=0)
    source: str | None = None
    meal_type: MealType | None = None
    course: Course | None = None
    yield_quantity: str
    yield_unit: str = Field(min_length=1)
    ingredients: list[RecipeIngredientWrite] = Field(default_factory=list)
    steps: list[RecipeStepWrite] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("yield_quantity")
    @classmethod
    def _validate_yield(cls, value: str) -> str:
        return _ensure_parseable(value)


class RecipeUpdate(RecipeCreate):
    # Optimistic-concurrency token; must match the recipe's current version.
    version: int


# --- Reads ------------------------------------------------------------------


class RecipeIngredientRead(BaseModel):
    ref_key: str
    ingredient: IngredientRead
    quantity_num: int | None
    quantity_den: int | None
    quantity_display: str | None
    unit: Unit | None
    preparation: str | None
    is_optional: bool
    section: str | None
    position: int


class RecipeStepRead(BaseModel):
    position: int
    section: str | None
    # `text_template` is the raw stored text (for editing); `text_rendered` has
    # its tokens resolved at the requested scale (for display).
    text_template: str
    text_rendered: str


class EffectiveYield(BaseModel):
    quantity_display: str
    unit: str


class RecipeRead(BaseModel):
    id: int
    created_at: int
    updated_at: int
    created_by: int
    version: int
    name: str
    description: str | None
    prep_time_minutes: int | None
    cook_time_minutes: int | None
    source: str | None
    meal_type: MealType | None
    course: Course | None
    # The scale this view was rendered at, as a quantity string ("1", "3/2").
    scale: str
    effective_yield: EffectiveYield
    ingredients: list[RecipeIngredientRead]
    steps: list[RecipeStepRead]
    tags: list[TagRead]


# --- Search results ---------------------------------------------------------


class SimilarRecipe(BaseModel):
    recipe: RecipeRead
    shared_count: int
    shared_ingredients: list[IngredientRead]


class MakeableRecipe(BaseModel):
    recipe: RecipeRead
    # Required, non-staple ingredients the cook lacks (presence-only).
    missing_ingredients: list[IngredientRead]
