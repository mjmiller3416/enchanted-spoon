"""app/utils/unit_conversion.py

Unit classification and conversion for shopping-list aggregation.

Quantities add only when they share a unit, or when they live in the same
measurable dimension and can be converted:

- mass: g, kg, oz, lb
- volume: tsp, tbsp, cup, ml, l, fl oz
- count: no unit, each, whole, piece, and the obvious synonyms

Everything else (clove, can, pinch, a unit we don't recognize) keeps its own
line. "to taste" and a missing amount stay quantity-less instead of becoming 0
added into a count.

MASS_UNITS, VOLUME_UNITS and COUNT_UNITS are the units the recipe form offers.
Aliases ("lbs", "pound(s)", "T", "tablespoon") fold onto those, plus the metric
and fluid-ounce units people import, without adding every spelling to the picker.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

# ── Dimension constants ─────────────────────────────────────────────────────────────────────────
DIMENSION_MASS = "mass"
DIMENSION_VOLUME = "volume"
DIMENSION_COUNT = "count"
DIMENSION_UNKNOWN = "unknown"


# ── Picker units ────────────────────────────────────────────────────────────────────────────────
# Keys are the values stored by the recipe form. Do not add aliases here:
# GET /api/unit-conversions/units lists these keys.

_OZ_IN_G = 28.3495
_LB_IN_G = 16 * _OZ_IN_G  # 453.592, so 1 lb is exactly 16 oz
_TSP_IN_ML = 4.92892
_TBSP_IN_ML = 3 * _TSP_IN_ML
_FL_OZ_IN_ML = 2 * _TBSP_IN_ML  # 1 fl oz is 2 tbsp
_CUP_IN_ML = 8 * _FL_OZ_IN_ML  # 1 cup is 8 fl oz

MASS_UNITS: dict[str, float] = {
    "oz": _OZ_IN_G,
    "lbs": _LB_IN_G,
}

VOLUME_UNITS: dict[str, float] = {
    "tsp": _TSP_IN_ML,
    "tbs": _TBSP_IN_ML,
    "cup": _CUP_IN_ML,
}

COUNT_UNITS: set[str] = {
    "",
    "stick",
    "bag",
    "box",
    "can",
    "jar",
    "package",
    "piece",
    "slice",
    "whole",
    "pinch",
    "dash",
    "to-taste",
}


# Canonical factors. Mass is grams, volume is milliliters.
_MASS: dict[str, float] = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": _OZ_IN_G,
    "lb": _LB_IN_G,
}

_VOLUME: dict[str, float] = {
    "ml": 1.0,
    "l": 1000.0,
    "tsp": _TSP_IN_ML,
    "tbsp": _TBSP_IN_ML,
    "fl oz": _FL_OZ_IN_ML,
    "cup": _CUP_IN_ML,
}

# These count words describe the same thing: one onion, however you say it.
_COUNT_SYNONYMS = {"", "each", "whole", "piece"}

_NON_QUANTITY = {"to taste"}

# Display labels for canonical units. Picker spellings ("lbs", "tbs") fold to these.
_DISPLAY = {
    "g": "g",
    "kg": "kg",
    "oz": "oz",
    "lb": "lb",
    "ml": "ml",
    "l": "l",
    "tsp": "tsp",
    "tbsp": "tbsp",
    "fl oz": "fl oz",
    "cup": "cup",
    "each": "each",
    "whole": "whole",
    "piece": "piece",
    "to taste": "to taste",
}

_ALIASES = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "oz": "oz",
    "ozs": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "l": "l",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "tsp": "tsp",
    "tsps": "tsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
    "t": "tsp",
    "tbsp": "tbsp",
    "tbs": "tbsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",
    "cup": "cup",
    "cups": "cup",
    "c": "cup",
    "fl oz": "fl oz",
    "floz": "fl oz",
    "fl ounce": "fl oz",
    "fl ounces": "fl oz",
    "fluid oz": "fl oz",
    "fluid ounce": "fl oz",
    "fluid ounces": "fl oz",
    "each": "each",
    "ea": "each",
    "eaches": "each",
    "unit": "each",
    "units": "each",
    "count": "each",
    "ct": "each",
    "cts": "each",
    "whole": "whole",
    "wholes": "whole",
    "piece": "piece",
    "pieces": "piece",
    "pc": "piece",
    "pcs": "piece",
    "to taste": "to taste",
    "totaste": "to taste",
    "tt": "to taste",
    "clove": "clove",
    "can": "can",
    "pinch": "pinch",
    "dash": "dash",
    "stick": "stick",
    "bag": "bag",
    "box": "box",
    "jar": "jar",
    "package": "package",
    "pkg": "package",
    "slice": "slice",
    "head": "head",
    "bunch": "bunch",
    "bottle": "bottle",
    "dozen": "dozen",
    "doz": "dozen",
}

# Largest first, so a mixed mass total lands on lb before oz.
_MASS_PREFERENCE = ("kg", "lb", "oz", "g")
_VOLUME_PREFERENCE = ("l", "cup", "fl oz", "tbsp", "tsp", "ml")

_FRIENDLY_FRACTIONS = (0.0, 0.125, 0.25, 1 / 3, 0.375, 0.5, 0.625, 2 / 3, 0.75, 0.875, 1.0)


# ── Normalization ───────────────────────────────────────────────────────────────────────────────
def _clean(unit: str | None) -> str:
    """Lowercase, strip punctuation, and collapse whitespace. A lone "T" stays tbsp."""
    if not unit:
        return ""
    raw = unit.strip()
    if raw in {"T", "T."}:
        return "tbsp"
    cleaned = raw.replace(".", " ").replace("-", " ")
    cleaned = cleaned.replace("(", "").replace(")", "")
    return " ".join(cleaned.lower().split())


def _fold_plural(unit: str) -> str:
    """Fold a trailing plural when the word isn't a known abbreviation."""
    for suffix in ("ches", "shes", "sses", "xes", "zes"):
        if unit.endswith(suffix) and len(unit) > len(suffix):
            return unit[:-2]
    if unit.endswith("oes") and len(unit) > 4:
        return unit[:-2]
    if unit.endswith("s") and not unit.endswith("ss") and len(unit) > 2:
        return unit[:-1]
    return unit


def canonical_unit(unit: str | None) -> str:
    """Map a unit spelling onto one canonical name. Empty means a bare count."""
    cleaned = _clean(unit)
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    folded = _fold_plural(cleaned)
    if folded in _ALIASES:
        return _ALIASES[folded]
    return folded


def normalize_unit(unit: str | None) -> str:
    """
    Normalize a unit string for consistent lookup.

    Returns the canonical unit, so "lbs", "lb." and "pounds" all come back "lb".
    """
    return canonical_unit(unit)


def _snap_number(quantity: float) -> float:
    """Drop binary dust and return a whole number when the value is one."""
    rounded = round(float(quantity), 4)
    nearest = round(rounded)
    if abs(rounded - nearest) < 1e-6:
        return float(nearest)
    return float(rounded)


def _round_measure(quantity: float, increment: float) -> float:
    """Keep a friendly fraction when the value already is one; otherwise round up."""
    if quantity <= 0:
        return 0.0
    whole = math.floor(quantity + 1e-9)
    frac = quantity - whole
    if frac >= 1 - 1e-9:
        return float(whole + 1)
    for target in _FRIENDLY_FRACTIONS:
        if abs(frac - target) <= 0.015:
            extra = 1.0 if target >= 1 - 1e-9 else target
            return _snap_number(whole + extra)
    steps = math.ceil((frac / increment) - 1e-9)
    return _snap_number(whole + steps * increment)


def round_to_friendly(quantity: float, unit: str) -> float:
    """
    Round a quantity for the shopping list.

    Mass and volume round up to a kitchen fraction when they aren't already on
    one, so 0.3 tsp becomes 3/8 tsp and 1.5 lb stays 1.5 lb. Counts, cloves,
    cans and the rest keep their sum (1/2 + 1/4 stays 3/4).
    """
    if quantity <= 0:
        return 0.0
    canonical = canonical_unit(unit)
    if canonical in {"g", "ml"}:
        return _round_measure(quantity, 1)
    if canonical in {"kg", "l"}:
        return _round_measure(quantity, 0.01)
    if canonical in _MASS or canonical in _VOLUME:
        return _round_measure(quantity, 0.125)
    return _snap_number(quantity)


def aggregation_bucket(unit: str | None) -> str:
    """
    Bucket a unit for shopping-list aggregation.

    Mass, volume and true counts each share one bucket. Any other unit gets
    its own bucket ("u:clove", "u:can") so those lines are never added together.
    The result always fits the 20-character contribution dimension column.
    """
    canonical = canonical_unit(unit)
    if canonical in _MASS:
        return DIMENSION_MASS
    if canonical in _VOLUME:
        return DIMENSION_VOLUME
    if canonical in _COUNT_SYNONYMS:
        return DIMENSION_COUNT
    slug = canonical.replace(" ", "-")
    return f"u:{slug}"[:20]


def get_dimension(unit: str | None) -> str:
    """Return the aggregation bucket for a unit. See aggregation_bucket."""
    return aggregation_bucket(unit)


def to_base_unit(quantity: float, unit: str | None) -> Tuple[float, str]:
    """
    Convert a quantity to its base unit within its dimension.

    Mass becomes grams, volume becomes milliliters. Counts and units that
    don't convert stay as written. "to taste" contributes nothing to add.
    """
    canonical = canonical_unit(unit)
    if canonical in _NON_QUANTITY:
        return 0.0, canonical
    if canonical in _MASS:
        return quantity * _MASS[canonical], "g"
    if canonical in _VOLUME:
        return quantity * _VOLUME[canonical], "ml"
    return quantity, canonical


def _source_canonicals(source_units: Sequence[str] | None, original_unit: str | None) -> list[str]:
    if source_units:
        return [canonical_unit(unit) for unit in source_units]
    if original_unit:
        return [canonical_unit(original_unit)]
    return []


def _matching(canonicals: Iterable[str], table: dict[str, float]) -> list[str]:
    return [unit for unit in canonicals if unit in table]


def _choose_measure(base_quantity: float, canonicals: Sequence[str], table: dict[str, float], preference: Sequence[str]) -> str:
    """Stay in the unit everyone used, or step up to the largest unit that holds at least 1."""
    used = _matching(canonicals, table)
    if used and len(set(used)) == 1:
        return used[0]
    for unit in preference:
        factor = table[unit]
        if base_quantity / factor >= 1 - 1e-6:
            return unit
    return preference[-1]


def _count_label(canonicals: Sequence[str]) -> str:
    """Show "whole" only when every line said whole. Mixed or bare counts show no unit."""
    if not canonicals:
        return ""
    labels = []
    for unit in canonicals:
        if unit in _COUNT_SYNONYMS and unit:
            labels.append(_DISPLAY[unit])
        elif unit == "":
            labels.append("")
        else:
            return ""
    distinct = set(labels)
    if len(distinct) == 1:
        return next(iter(distinct))
    return ""


def _bucket_label(dimension: str) -> str:
    slug = dimension[2:] if dimension.startswith("u:") else dimension
    label = slug.replace("-", " ")
    return _DISPLAY.get(label, label)


def to_display_unit(
    base_quantity: float,
    dimension: str,
    original_unit: str | None = None,
    source_units: Sequence[str] | None = None,
) -> Tuple[float, str]:
    """
    Convert a base-unit total into the unit a shopper should read.

    Mixed convertible units pick a sensible scale (8 oz + 1 lb is 1.5 lb).
    A total that was all cups stays in cups. "to taste" displays as words,
    with quantity 0 so it is not a number to add.
    """
    canonicals = _source_canonicals(source_units, original_unit)
    label = _bucket_label(dimension) if dimension.startswith("u:") else ""
    if label == "to taste" or (canonicals and all(unit == "to taste" for unit in canonicals)):
        return 0.0, "to taste"

    if dimension == DIMENSION_MASS:
        chosen = _choose_measure(base_quantity, canonicals, _MASS, _MASS_PREFERENCE)
        quantity = base_quantity / _MASS[chosen]
        return round_to_friendly(quantity, chosen), _DISPLAY[chosen]

    if dimension == DIMENSION_VOLUME:
        chosen = _choose_measure(base_quantity, canonicals, _VOLUME, _VOLUME_PREFERENCE)
        quantity = base_quantity / _VOLUME[chosen]
        return round_to_friendly(quantity, chosen), _DISPLAY[chosen]

    if dimension == DIMENSION_COUNT:
        return round_to_friendly(base_quantity, ""), _count_label(canonicals)

    return round_to_friendly(base_quantity, label), label


def quantity_in_unit(base_quantity: float, dimension: str, display_unit: str) -> float:
    """Express a base quantity in a display unit already chosen for its group."""
    if display_unit == "to taste":
        return 0.0
    canonical = canonical_unit(display_unit)
    if dimension == DIMENSION_MASS and canonical in _MASS:
        return round_to_friendly(base_quantity / _MASS[canonical], canonical)
    if dimension == DIMENSION_VOLUME and canonical in _VOLUME:
        return round_to_friendly(base_quantity / _VOLUME[canonical], canonical)
    return round_to_friendly(base_quantity, display_unit or "")
