"""app/utils/spoken_items.py

Turns what someone said to Alexa ("a gallon of milk and two cans of black
beans") into shopping-list items: a name, a quantity and maybe a unit.

- Several items split on "and", "plus" and commas, unless the whole phrase
  is one food ("mac and cheese", "half and half", or anything the caller's
  ``is_known_item`` recognises, such as an ingredient in the person's library).
- A leading amount ("a", "two", "3", "half a", "a couple of") becomes the
  quantity, 1 when none is said.
- A unit after the amount ("gallon", "cans of", "a bag of") becomes the unit.
  Packaging words (bag, box, can...) count as a unit only before "of", so
  "two rolls" stays two rolls and "a roll of paper towels" is 1 roll.
- Trailing "to my shopping list"-style phrases and "please" are dropped, in
  case Alexa left them in the slot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

NUMBER_WORDS = {
    "a": 1.0, "an": 1.0, "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0, "eleven": 11.0,
    "twelve": 12.0, "thirteen": 13.0, "fourteen": 14.0, "fifteen": 15.0, "sixteen": 16.0,
    "seventeen": 17.0, "eighteen": 18.0, "nineteen": 19.0, "twenty": 20.0,
}

# Measures may skip "of" ("two pounds ground beef", "a dozen eggs").
MEASURE_UNITS = {
    "gallon": "gallon", "gallons": "gallon",
    "quart": "quart", "quarts": "quart",
    "pint": "pint", "pints": "pint",
    "liter": "liter", "liters": "liter", "litre": "liter", "litres": "liter",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
    "gram": "g", "grams": "g",
    "dozen": "dozen",
}

# Packaging is a unit only when "of" follows.
PACKAGE_UNITS = {
    "bag": "bag", "bags": "bag",
    "box": "box", "boxes": "box",
    "can": "can", "cans": "can",
    "jar": "jar", "jars": "jar",
    "bottle": "bottle", "bottles": "bottle",
    "carton": "carton", "cartons": "carton",
    "pack": "pack", "packs": "pack", "package": "package", "packages": "package",
    "packet": "packet", "packets": "packet",
    "loaf": "loaf", "loaves": "loaf",
    "bunch": "bunch", "bunches": "bunch",
    "head": "head", "heads": "head",
    "case": "case", "cases": "case",
    "container": "container", "containers": "container",
    "stick": "stick", "sticks": "stick",
    "block": "block", "blocks": "block",
    "tub": "tub", "tubs": "tub",
    "roll": "roll", "rolls": "roll",
    "bar": "bar", "bars": "bar",
}

# Foods whose names contain "and"; never split.
KEEP_TOGETHER = {
    "half and half", "mac and cheese", "macaroni and cheese", "pork and beans",
    "salt and vinegar chips", "sour cream and onion chips", "peanut butter and jelly",
    "chips and salsa", "rice and beans", "biscuits and gravy", "cookies and cream",
    "fish and chips",
}

_FILLER_PREFIXES = ("some more ", "some ", "more ", "another ", "a few ", "a little ", "extra ")
_TRAILING_LIST = re.compile(
    r"\s+(?:to|on|onto|in|into)\s+(?:my|the|our)(?:\s+\w+){0,2}\s+list$"
)
_TRAILING_POLITE = re.compile(r"(?:\s+please|\s+thanks|\s+thank you)+$")
# "and" splits items, except in "one and a half"
_SPLIT = re.compile(r"\s*,\s*(?:and\s+)?|\s+and\s+(?!a half\b)|\s+plus\s+|\s*&\s*")
_NUMBER = re.compile(r"^\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class SpokenItem:
    """One item as said: ``spoken`` is the cleaned words, for repeating back."""

    name: str
    quantity: float
    unit: Optional[str]
    spoken: str


def _clean(phrase: str) -> str:
    text = " ".join(phrase.lower().replace("’", "'").split())
    text = text.strip(" .!?")
    text = _TRAILING_POLITE.sub("", text)
    text = _TRAILING_LIST.sub("", text)
    return text.strip(" ,.")


def _take_amount(words: List[str]) -> Tuple[Optional[float], List[str]]:
    """A leading amount, and the words after it."""
    if not words:
        return None, words
    lowered = " ".join(words)
    for prefix, amount in (("a couple of ", 2.0), ("a couple ", 2.0), ("a half ", 0.5), ("half a ", 0.5),
                           ("half an ", 0.5), ("a half of ", 0.5), ("half ", 0.5)):
        if lowered.startswith(prefix):
            return amount, words[len(prefix.split()):]
    first = words[0]
    if _NUMBER.match(first):
        return float(first), words[1:]
    if first in NUMBER_WORDS:
        rest = words[1:]
        # "a half gallon", "one and a half pounds"
        if rest[:3] == ["and", "a", "half"]:
            return NUMBER_WORDS[first] + 0.5, rest[3:]
        if first in ("a", "an") and rest[:1] == ["half"]:
            return 0.5, rest[1:]
        return NUMBER_WORDS[first], rest
    return None, words


def _take_unit(words: List[str]) -> Tuple[Optional[str], List[str]]:
    """A unit at the front, and the words after it (dropping "of")."""
    if len(words) < 2:
        return None, words
    first, rest = words[0], words[1:]
    has_of = rest[0] == "of"
    if first in MEASURE_UNITS:
        rest = rest[1:] if has_of else rest
        return (MEASURE_UNITS[first], rest) if rest else (None, words)
    if first in PACKAGE_UNITS and has_of and len(rest) > 1:
        return PACKAGE_UNITS[first], rest[1:]
    return None, words


def parse_one(fragment: str) -> Optional[SpokenItem]:
    """One item from a fragment ("2 cans of tuna"), or None if nothing's left of it."""
    text = _clean(fragment)
    for prefix in _FILLER_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    words = text.split()
    amount, words = _take_amount(words)
    unit, words = _take_unit(words)
    if words[:1] == ["of"]:  # "a couple of", "a half of"
        words = words[1:]
    name = " ".join(words).strip(" ,.")
    if not name or name in NUMBER_WORDS:
        return None
    return SpokenItem(name=name[:255], quantity=amount if amount is not None else 1.0, unit=unit, spoken=text)


def parse_spoken_items(
    phrase: Optional[str],
    is_known_item: Callable[[str], bool] = lambda _name: False,
) -> List[SpokenItem]:
    """Every item in what was said, in order, without repeats.

    Args:
        phrase: The slot value Alexa heard.
        is_known_item: True for a name that must stay whole (e.g. an
            ingredient in the person's library, "mac and cheese").

    Returns:
        List[SpokenItem]: Possibly empty.
    """
    if not phrase:
        return []
    text = _clean(phrase)
    if not text:
        return []
    if text in KEEP_TOGETHER or is_known_item(text):  # "half and half" said on its own
        return [SpokenItem(name=text[:255], quantity=1.0, unit=None, spoken=text)]
    whole = parse_one(text)
    if whole is not None and (whole.name in KEEP_TOGETHER or is_known_item(whole.name)):
        return [whole]

    items: List[SpokenItem] = []
    seen: set[str] = set()
    for part in _SPLIT.split(text):
        item = parse_one(part)
        if item is None or item.name in seen:
            continue
        seen.add(item.name)
        items.append(item)
    return items
