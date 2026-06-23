"""Enumerations for the recipes domain.

All are `str` enums so they serialize to readable values in JSON and store as
their string value in the database (matching the codebase convention used by
`LaundryStatus`). `Unit` values are the compact tokens stored on
`RecipeIngredient.unit` and referenced by step templates.
"""

import enum


class Dimension(str, enum.Enum):
    """The physical quantity a unit measures.

    Conversion is only meaningful within a dimension. `INFORMAL` groups units
    that have no fixed magnitude (a "pinch", "to taste") and so never convert.
    """

    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"
    INFORMAL = "informal"


class Unit(str, enum.Enum):
    # Mass
    GRAM = "g"
    KILOGRAM = "kg"
    OUNCE = "oz"
    POUND = "lb"
    # Volume
    MILLILITER = "ml"
    LITER = "l"
    TSP = "tsp"
    TBSP = "tbsp"
    CUP = "cup"
    FLOZ = "fl_oz"
    # Count
    PIECE = "piece"
    CLOVE = "clove"
    SLICE = "slice"
    # Informal (no fixed magnitude)
    PINCH = "pinch"
    DASH = "dash"
    TO_TASTE = "to_taste"


class IngredientCategory(str, enum.Enum):
    PRODUCE = "produce"
    DAIRY = "dairy"
    MEAT_SEAFOOD = "meat_seafood"
    BAKERY = "bakery"
    PANTRY = "pantry"
    CANNED = "canned"
    FROZEN = "frozen"
    SPICES = "spices"
    CONDIMENTS = "condiments"
    BEVERAGES = "beverages"
    SNACKS = "snacks"
    BAKING = "baking"
    DELI = "deli"
    OTHER = "other"


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DESSERT = "dessert"


class Course(str, enum.Enum):
    APPETIZER = "appetizer"
    MAIN = "main"
    SIDE = "side"
    DRINK = "drink"
    SAUCE = "sauce"
