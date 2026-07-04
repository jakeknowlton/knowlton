"""SQLModel tables for the recipes domain.

Two clusters live here: the shared **catalog** (`Ingredient`, `IngredientAlias`,
`Tag`) and the **recipe aggregate** (`Recipe` + its `RecipeIngredient`,
`RecipeStep`, `RecipeTag` children). The catalog is global and append-only in v1;
the aggregate is owned by its `Recipe` and cascades on delete via ORM
relationships (portable across SQLite-now / Postgres-later, which is why we avoid
DB-engine `ON DELETE`).
"""

# SQLModel's `Relationship(...)` is typed to return `Any`, so every relationship
# attribute assignment below trips `reportAny`. That is the canonical declaration
# idiom and unavoidable in our code, so the rule is relaxed for this table-only
# module (real `Any` leaks in hand-written logic are still caught elsewhere).
# pyright: reportAny=false

import enum
from typing import ClassVar, cast

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.sql.schema import SchemaItem
from sqlmodel import Field, Relationship, SQLModel

from food.recipes.enums import Course, IngredientCategory, MealType, Unit


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    # `Enum.value` is typed `Any` upstream; these are all `str` enums, so the cast
    # restores the real element type without a runtime change.
    return [cast(str, member.value) for member in enum_cls]


def _enum_column(enum_cls: type[enum.Enum], *, nullable: bool) -> Column[str]:
    """A column that stores an enum by its string `value` (matching `LaundryStatus`)."""
    return Column(
        SAEnum(enum_cls, values_callable=_enum_values),
        nullable=nullable,
    )


# --- Catalog ----------------------------------------------------------------


class Ingredient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    # Dedup key: lowercased, whitespace-collapsed name. UNIQUE so get-or-create
    # converges on a single row per ingredient regardless of how it was typed.
    name_normalized: str = Field(unique=True, index=True)
    category: IngredientCategory | None = Field(
        default=None, sa_column=_enum_column(IngredientCategory, nullable=True)
    )
    is_staple: bool = Field(default=False)
    created_at: int  # Unix timestamp


class IngredientAlias(SQLModel, table=True):
    """A second name that resolves to an existing `Ingredient` (e.g. "scallion"
    -> "green onion"). Created out-of-band; not exposed for mutation in v1."""

    id: int | None = Field(default=None, primary_key=True)
    alias_normalized: str = Field(unique=True, index=True)
    ingredient_id: int = Field(foreign_key="ingredient.id")


class Tag(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    name_normalized: str = Field(unique=True, index=True)
    created_at: int  # Unix timestamp


# --- Recipe aggregate -------------------------------------------------------


class Recipe(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: int  # Unix timestamp
    updated_at: int  # Unix timestamp
    created_by: int = Field(foreign_key="user.id")
    # Optimistic-concurrency token: bumped on every successful PUT; a stale
    # version on update is rejected with 409.
    version: int = Field(default=1)

    name: str
    description: str | None = Field(default=None)
    prep_time_minutes: int | None = Field(default=None)
    cook_time_minutes: int | None = Field(default=None)
    source: str | None = Field(default=None)
    meal_type: MealType | None = Field(
        default=None, sa_column=_enum_column(MealType, nullable=True)
    )
    course: Course | None = Field(
        default=None, sa_column=_enum_column(Course, nullable=True)
    )

    # Yield as an exact rational plus a free-text unit label ("servings",
    # "cookies"). Scaling reads multiply this by the requested factor.
    yield_quantity_num: int
    yield_quantity_den: int
    yield_unit: str

    ingredients: list["RecipeIngredient"] = Relationship(
        back_populates="recipe",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "RecipeIngredient.position",
        },
    )
    steps: list["RecipeStep"] = Relationship(
        back_populates="recipe",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "RecipeStep.position",
        },
    )
    tags: list["RecipeTag"] = Relationship(
        back_populates="recipe",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class RecipeIngredient(SQLModel, table=True):
    # `ref_key` is the stable handle a step template uses to refer to this line
    # (e.g. "flour"); unique per recipe. The ingredient_id index powers the
    # shared-ingredient searches (filter / similar / makeable).
    __table_args__: ClassVar[tuple[SchemaItem, ...]] = (
        UniqueConstraint("recipe_id", "ref_key", name="uq_recipe_ingredient_ref_key"),
        Index("ix_recipe_ingredient_ingredient_id", "ingredient_id"),
        Index("ix_recipe_ingredient_recipe_id", "recipe_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    # Populated by the `Recipe.ingredients` relationship on flush, so it carries
    # a default to stay constructible without it; `nullable=False` keeps the
    # column NOT NULL at the DB level (mirrors how `id` is declared Optional).
    recipe_id: int | None = Field(default=None, foreign_key="recipe.id", nullable=False)
    ingredient_id: int = Field(foreign_key="ingredient.id")
    ref_key: str

    # Nullable for informal amounts ("salt, to taste"). Stored as a reduced
    # rational pair so scaling stays exact.
    quantity_num: int | None = Field(default=None)
    quantity_den: int | None = Field(default=None)
    unit: Unit | None = Field(default=None, sa_column=_enum_column(Unit, nullable=True))
    preparation: str | None = Field(default=None)
    is_optional: bool = Field(default=False)
    section: str | None = Field(default=None)
    position: int

    recipe: Recipe = Relationship(back_populates="ingredients")
    ingredient: Ingredient = Relationship()


class RecipeStep(SQLModel, table=True):
    __table_args__: ClassVar[tuple[SchemaItem, ...]] = (
        Index("ix_recipe_step_recipe_id", "recipe_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    # Populated by the `Recipe.steps` relationship on flush (see RecipeIngredient).
    recipe_id: int | None = Field(default=None, foreign_key="recipe.id", nullable=False)
    position: int
    section: str | None = Field(default=None)
    # Raw template text; may embed `{{ri:<ref_key>}}` tokens resolved on read.
    text: str

    recipe: Recipe = Relationship(back_populates="steps")


class RecipeTag(SQLModel, table=True):
    # `recipe_id` is populated by the `Recipe.tags` relationship on flush, so it
    # defaults to None to stay constructible; as a primary-key column it is NOT
    # NULL regardless. `tag_id` is always supplied explicitly.
    recipe_id: int | None = Field(
        default=None, foreign_key="recipe.id", primary_key=True
    )
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)

    recipe: Recipe = Relationship(back_populates="tags")
    tag: Tag = Relationship()
