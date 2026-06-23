"""Rational quantities: parse, store, render, and scale exactly.

Quantities are kept as :class:`fractions.Fraction` end to end so that scaling is
exact (``1/3 * 3 == 1``, never ``0.999...``). On the database they live as a
reduced ``(numerator, denominator)`` integer pair; in the API they are written
as human strings (``"1 1/2"``) and read back as a mixed-number display string
alongside the raw columns.
"""

from fractions import Fraction


class InvalidQuantityError(Exception):
    """Raised when a quantity string is unparseable or not strictly positive."""


def parse_quantity(raw: str) -> Fraction:
    """Parse a human quantity into an exact ``Fraction``.

    Accepts whole numbers (``"2"``), mixed numbers (``"1 1/2"``), improper
    fractions (``"3/2"``), and decimals (``"0.5"``). Rejects non-positive values
    and zero denominators with :class:`InvalidQuantityError`.
    """
    text = raw.strip()
    if not text:
        raise InvalidQuantityError("Quantity is empty")

    parts = text.split()
    try:
        if len(parts) == 1:
            value = Fraction(parts[0])
        elif len(parts) == 2:
            whole = Fraction(parts[0])
            frac = Fraction(parts[1])
            if whole.denominator != 1 or whole < 0 or frac < 0:
                raise InvalidQuantityError(f"Malformed mixed number: {raw!r}")
            value = whole + frac
        else:
            raise InvalidQuantityError(f"Cannot parse quantity: {raw!r}")
    except (ValueError, ZeroDivisionError) as exc:
        raise InvalidQuantityError(f"Cannot parse quantity: {raw!r}") from exc

    if value <= 0:
        raise InvalidQuantityError(f"Quantity must be positive: {raw!r}")
    return value


def to_columns(q: Fraction) -> tuple[int, int]:
    """The reduced ``(numerator, denominator)`` pair for storage."""
    return q.numerator, q.denominator


def from_columns(num: int, den: int) -> Fraction:
    """Rebuild a ``Fraction`` from stored columns (auto-reduces)."""
    return Fraction(num, den)


def format_quantity(q: Fraction) -> str:
    """Render a positive ``Fraction`` as a mixed number.

    ``9/2`` -> ``"4 1/2"``, ``1/3`` -> ``"1/3"``, ``2/1`` -> ``"2"``.
    """
    whole = q.numerator // q.denominator
    remainder = q - whole
    if remainder == 0:
        return str(whole)
    fraction_part = f"{remainder.numerator}/{remainder.denominator}"
    if whole == 0:
        return fraction_part
    return f"{whole} {fraction_part}"


def scale(q: Fraction, factor: Fraction) -> Fraction:
    """Multiply a quantity by a scaling factor, exactly."""
    return q * factor
