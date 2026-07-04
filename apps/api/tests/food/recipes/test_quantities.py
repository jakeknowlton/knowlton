from fractions import Fraction

import pytest

from food.recipes.quantities import (
    InvalidQuantityError,
    format_quantity,
    from_columns,
    parse_quantity,
    scale,
    to_columns,
)

# --- parse_quantity ---------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2", Fraction(2)),
        ("1 1/2", Fraction(3, 2)),
        ("3/2", Fraction(3, 2)),
        ("0.5", Fraction(1, 2)),
        ("  4  ", Fraction(4)),
        ("2 3/4", Fraction(11, 4)),
        ("10/5", Fraction(2)),  # reduces
    ],
)
def test_parse_quantity_accepts(raw: str, expected: Fraction) -> None:
    assert parse_quantity(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "0",
        "-1",
        "-1/2",
        "3/0",
        "abc",
        "1 2 3",
        "1/2/3",
    ],
)
def test_parse_quantity_rejects(raw: str) -> None:
    with pytest.raises(InvalidQuantityError):
        _ = parse_quantity(raw)


# --- columns round-trip -----------------------------------------------------


def test_to_columns_is_reduced() -> None:
    assert to_columns(Fraction(10, 5)) == (2, 1)
    assert to_columns(Fraction(3, 6)) == (1, 2)


def test_columns_round_trip() -> None:
    q = Fraction(7, 4)
    num, den = to_columns(q)
    assert from_columns(num, den) == q


# --- format_quantity --------------------------------------------------------


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        (Fraction(9, 2), "4 1/2"),
        (Fraction(1, 3), "1/3"),
        (Fraction(2, 1), "2"),
        (Fraction(11, 4), "2 3/4"),
        (Fraction(1), "1"),
    ],
)
def test_format_quantity(q: Fraction, expected: str) -> None:
    assert format_quantity(q) == expected


def test_parse_format_round_trip() -> None:
    for raw in ["2", "1 1/2", "3/4", "4 1/2"]:
        assert format_quantity(parse_quantity(raw)) == raw


# --- scale ------------------------------------------------------------------


def test_scale_is_exact() -> None:
    # The whole point of rationals: a third, tripled, is exactly one.
    assert scale(Fraction(1, 3), Fraction(3)) == Fraction(1)


def test_scale_half() -> None:
    assert scale(Fraction(4), Fraction(1, 2)) == Fraction(2)
    assert scale(Fraction(3), Fraction(3, 2)) == Fraction(9, 2)
