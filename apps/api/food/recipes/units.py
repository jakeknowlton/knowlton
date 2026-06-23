"""Units of measure: dimension/factor metadata and within-dimension conversion.

`convert` is pure and exact. It is *not* used by recipe scaling yet (that uses
plain rational multiplication in `quantities.scale`); it is built here for the
future grocery-aggregation feature, which needs to combine amounts expressed in
mixed units.

The base-factor map is typed `Fraction | None` rather than `float` (as an earlier
draft proposed): the codebase trades on exact rational arithmetic, and `convert`
returns a `Fraction`, so float factors would silently reintroduce binary
rounding. Factors are the exact ratio of each unit to its dimension's base unit
(gram for MASS, milliliter for VOLUME, one item for COUNT). INFORMAL units have
no fixed magnitude, so their factor is `None` and they never convert.
"""

from fractions import Fraction

from food.recipes.enums import Dimension, Unit

# Exact conversion constants for the customary units, defined once so the
# derived units stay exactly proportional.
_POUND_G = Fraction(45359237, 100_000)  # 453.59237 g — international pound
_FLOZ_ML = Fraction(295735295625, 10_000_000_000)  # 29.5735295625 ml — US fl oz


class IncompatibleUnitsError(Exception):
    """Raised when two units cannot be converted (different or informal dimensions)."""


UNIT_META: dict[Unit, tuple[Dimension, Fraction | None]] = {
    # Mass (base: gram)
    Unit.GRAM: (Dimension.MASS, Fraction(1)),
    Unit.KILOGRAM: (Dimension.MASS, Fraction(1000)),
    Unit.OUNCE: (Dimension.MASS, _POUND_G / 16),
    Unit.POUND: (Dimension.MASS, _POUND_G),
    # Volume (base: milliliter)
    Unit.MILLILITER: (Dimension.VOLUME, Fraction(1)),
    Unit.LITER: (Dimension.VOLUME, Fraction(1000)),
    Unit.TSP: (Dimension.VOLUME, _FLOZ_ML / 6),
    Unit.TBSP: (Dimension.VOLUME, _FLOZ_ML / 2),
    Unit.CUP: (Dimension.VOLUME, _FLOZ_ML * 8),
    Unit.FLOZ: (Dimension.VOLUME, _FLOZ_ML),
    # Count (base: one item)
    Unit.PIECE: (Dimension.COUNT, Fraction(1)),
    Unit.CLOVE: (Dimension.COUNT, Fraction(1)),
    Unit.SLICE: (Dimension.COUNT, Fraction(1)),
    # Informal (no fixed magnitude)
    Unit.PINCH: (Dimension.INFORMAL, None),
    Unit.DASH: (Dimension.INFORMAL, None),
    Unit.TO_TASTE: (Dimension.INFORMAL, None),
}

# Human-readable singular/plural labels. Abbreviations are invariant; spelled-out
# units pluralize.
_DISPLAY: dict[Unit, tuple[str, str]] = {
    Unit.GRAM: ("g", "g"),
    Unit.KILOGRAM: ("kg", "kg"),
    Unit.OUNCE: ("oz", "oz"),
    Unit.POUND: ("lb", "lb"),
    Unit.MILLILITER: ("ml", "ml"),
    Unit.LITER: ("l", "l"),
    Unit.TSP: ("tsp", "tsp"),
    Unit.TBSP: ("tbsp", "tbsp"),
    Unit.CUP: ("cup", "cups"),
    Unit.FLOZ: ("fl oz", "fl oz"),
    Unit.PIECE: ("piece", "pieces"),
    Unit.CLOVE: ("clove", "cloves"),
    Unit.SLICE: ("slice", "slices"),
    Unit.PINCH: ("pinch", "pinches"),
    Unit.DASH: ("dash", "dashes"),
    Unit.TO_TASTE: ("to taste", "to taste"),
}


def unit_display(unit: Unit, plural: bool) -> str:
    """The human label for a unit, e.g. ``cup``/``cups``, ``to_taste`` -> "to taste"."""
    singular, plural_form = _DISPLAY[unit]
    return plural_form if plural else singular


def convert(value: Fraction, frm: Unit, to: Unit) -> Fraction:
    """Convert ``value`` from one unit to another within the same dimension.

    Raises ``IncompatibleUnitsError`` across dimensions or for INFORMAL units.
    """
    dim_from, factor_from = UNIT_META[frm]
    dim_to, factor_to = UNIT_META[to]
    if factor_from is None or factor_to is None or dim_from != dim_to:
        raise IncompatibleUnitsError(f"Cannot convert {frm.value} to {to.value}")
    return value * factor_from / factor_to
