"""The fixed tag vocabulary shared by the parse agent and customer wish lists.

Matching is a single Firestore `array-contains-any` query over these tags
(design.md §4), so both sides MUST use exactly this list.
"""

from __future__ import annotations

from typing import Literal

TAGS: tuple[str, ...] = (
    "salad",
    "pizza",
    "sushi",
    "burger",
    "dessert",
    "bakery",
    "coffee",
    "sandwich",
    "pasta",
    "grill",
    "seafood",
    "juice",
    "breakfast",
    "vegan",
    "snack",
)

Tag = Literal[
    "salad",
    "pizza",
    "sushi",
    "burger",
    "dessert",
    "bakery",
    "coffee",
    "sandwich",
    "pasta",
    "grill",
    "seafood",
    "juice",
    "breakfast",
    "vegan",
    "snack",
]

# Keep the Literal (used by pydantic / the model schema) and the tuple in sync.
assert set(Tag.__args__) == set(TAGS), "tags.Tag and tags.TAGS are out of sync"


def is_tag(value: str) -> bool:
    return value in TAGS


def tag_list_for_prompt() -> str:
    return ", ".join(TAGS)
