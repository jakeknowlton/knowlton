from fractions import Fraction

import pytest

from food.recipes.enums import Dimension, Unit
from food.recipes.units import (
    UNIT_META,
    IncompatibleUnitsError,
    convert,
    unit_display,
)

# --- metadata coverage ------------------------------------------------------


def test_every_unit_has_metadata() -> None:
    assert set(UNIT_META) == set(Unit)


def test_informal_units_have_no_factor() -> None:
    for unit, (dimension, factor) in UNIT_META.items():
        if dimension is Dimension.INFORMAL:
            assert factor is None
        else:
            assert factor is not None


# --- unit_display -----------------------------------------------------------


@pytest.mark.parametrize(
    ("unit", "plural", "expected"),
    [
        (Unit.CUP, False, "cup"),
        (Unit.CUP, True, "cups"),
        (Unit.TO_TASTE, False, "to taste"),
        (Unit.TO_TASTE, True, "to taste"),
        (Unit.GRAM, True, "g"),
        (Unit.SLICE, True, "slices"),
        (Unit.FLOZ, False, "fl oz"),
    ],
)
def test_unit_display(unit: Unit, plural: bool, expected: str) -> None:
    assert unit_display(unit, plural) == expected


# --- convert (within dimension) ---------------------------------------------


def test_convert_mass_exact() -> None:
    assert convert(Fraction(1), Unit.KILOGRAM, Unit.GRAM) == Fraction(1000)
    assert convert(Fraction(1000), Unit.GRAM, Unit.KILOGRAM) == Fraction(1)


def test_convert_pound_to_ounce() -> None:
    assert convert(Fraction(1), Unit.POUND, Unit.OUNCE) == Fraction(16)


def test_convert_volume_exact() -> None:
    assert convert(Fraction(1), Unit.TBSP, Unit.TSP) == Fraction(3)
    assert convert(Fraction(1), Unit.CUP, Unit.FLOZ) == Fraction(8)


def test_convert_identity() -> None:
    assert convert(Fraction(5), Unit.GRAM, Unit.GRAM) == Fraction(5)


def test_convert_round_trip_is_exact() -> None:
    grams = convert(Fraction(1), Unit.CUP, Unit.MILLILITER)
    assert convert(grams, Unit.MILLILITER, Unit.CUP) == Fraction(1)


# --- convert (incompatible) -------------------------------------------------


def test_convert_across_dimensions_raises() -> None:
    with pytest.raises(IncompatibleUnitsError):
        convert(Fraction(1), Unit.GRAM, Unit.MILLILITER)


def test_convert_informal_raises() -> None:
    with pytest.raises(IncompatibleUnitsError):
        convert(Fraction(1), Unit.PINCH, Unit.GRAM)
    with pytest.raises(IncompatibleUnitsError):
        convert(Fraction(1), Unit.TO_TASTE, Unit.TO_TASTE)
