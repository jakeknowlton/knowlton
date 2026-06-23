"""Step-text token grammar.

A step's stored text may embed references to the recipe's ingredient lines so the
amounts stay in sync with scaling. Tokens:

    {{ri:<ref_key>}}            amount + name, e.g. "4 cups flour"
    {{ri:<ref_key>|amount}}     amount only,  e.g. "4 cups"
    {{ri:<ref_key>|name}}       name only,    e.g. "flour"
    {{ri:<ref_key>*<n>/<d>}}    amount + name, with the amount further multiplied
                                by n/d (for "add half the flour" steps)

Amounts are computed from the *base* ingredient quantity times the requested
`scale` (times any per-token multiplier). A null quantity renders just the unit
display ("to taste"); time and temperature literals in the prose are never
touched.
"""

import re
from dataclasses import dataclass
from fractions import Fraction

from food.recipes.enums import Unit
from food.recipes.quantities import format_quantity
from food.recipes.units import unit_display

_TOKEN = re.compile(
    r"\{\{ri:(?P<ref>[a-z0-9_-]+)"
    r"(?:\*(?P<num>\d+)/(?P<den>\d+)|\|(?P<sel>name|amount))?\}\}"
)


@dataclass(frozen=True)
class IngredientRef:
    """What a token needs to render an ingredient line.

    `quantity` is the *base* amount (recipe scale not yet applied); `render`
    applies the scale so a single source of scale lives in the caller.
    """

    quantity: Fraction | None
    unit: Unit | None
    name: str


def extract_refs(text: str) -> set[str]:
    """The set of ref_keys a step's tokens point at (for write-time validation)."""
    return {match.group("ref") for match in _TOKEN.finditer(text)}


def _format_amount(quantity: Fraction | None, unit: Unit | None) -> str:
    if quantity is None:
        # Informal / unmeasured: the unit *is* the amount ("to taste", "pinch").
        return unit_display(unit, plural=False) if unit is not None else ""
    number = format_quantity(quantity)
    if unit is None:
        return number
    return f"{number} {unit_display(unit, plural=quantity > 1)}"


def render(text: str, refs: dict[str, IngredientRef], scale: Fraction) -> str:
    """Resolve ingredient tokens in `text` at the given recipe `scale`."""

    def replace(match: re.Match[str]) -> str:
        ref = refs.get(match.group("ref"))
        if ref is None:
            # Write/update validation guarantees referenced keys exist; if one
            # slips through, leave the raw token rather than crashing a read.
            return match.group(0)

        quantity = ref.quantity
        if quantity is not None:
            quantity = quantity * scale
            if match.group("num") is not None:
                quantity = quantity * Fraction(
                    int(match.group("num")), int(match.group("den"))
                )

        selector = match.group("sel")
        if selector == "name":
            return ref.name
        amount = _format_amount(quantity, ref.unit)
        if selector == "amount":
            return amount
        return f"{amount} {ref.name}".strip()

    return _TOKEN.sub(replace, text)
