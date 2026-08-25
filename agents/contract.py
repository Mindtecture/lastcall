"""Parse agent output contract (design.md §5), enforced with pydantic.

Every inbound business message is classified into exactly one intent and the
fields that intent needs. Anything the model is unsure about must come back
as `unknown` — the pipeline never guesses its way into a published offer.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from agents.tags import Tag

Intent = Literal["new_offer", "approve", "revise", "pickup_code", "unknown"]

# Below this the pipeline treats the result as `unknown` (design.md §5).
CONFIDENCE_THRESHOLD = 0.6

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_CODE_RE = re.compile(r"^\d{4}$")


class ParseResult(BaseModel):
    """Strict JSON returned by the parse agent."""

    intent: Intent
    item_label: Optional[str] = Field(
        default=None,
        description="Short item name as the business wrote it, e.g. 'salads'.",
    )
    tags: list[Tag] = Field(
        default_factory=list,
        description="Tags from the fixed list that describe the item.",
    )
    qty: Optional[int] = Field(default=None, description="Number of units available.")
    explicit_price: Optional[float] = Field(
        default=None,
        description=(
            "Per-unit price the business stated, in currency units (e.g. 4.0). "
            "Null if not stated."
        ),
    )
    expiry_time: Optional[str] = Field(
        default=None, description="Pickup deadline as 24h 'HH:MM', e.g. '21:00'."
    )
    code: Optional[str] = Field(
        default=None, description="4-digit pickup code, digits only."
    )
    confidence: float = Field(description="0.0-1.0 confidence in the classification.")

    # --- normalisation & validation -------------------------------------

    @field_validator("item_label", mode="before")
    @classmethod
    def _clean_label(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @field_validator("qty")
    @classmethod
    def _qty_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("qty must be positive")
        return v

    @field_validator("explicit_price")
    @classmethod
    def _price_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError("explicit_price must be >= 0")
        return v

    @field_validator("expiry_time", mode="before")
    @classmethod
    def _time_format(cls, v):
        if v in (None, ""):
            return None
        if not isinstance(v, str) or not _TIME_RE.match(v.strip()):
            raise ValueError("expiry_time must be 24h HH:MM")
        return v.strip()

    @field_validator("code", mode="before")
    @classmethod
    def _code_format(cls, v):
        if v in (None, ""):
            return None
        v = str(v).strip()
        if not _CODE_RE.match(v):
            raise ValueError("code must be exactly 4 digits")
        return v

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be within 0..1")
        return v

    # --- helpers ---------------------------------------------------------

    def gated(self) -> "ParseResult":
        """Apply the confidence gate: low confidence collapses to `unknown`."""
        if self.intent != "unknown" and self.confidence < CONFIDENCE_THRESHOLD:
            return self.model_copy(update={"intent": "unknown"})
        return self

    @classmethod
    def unknown(cls) -> "ParseResult":
        """Fallback result when the model could not produce valid output."""
        return cls(intent="unknown", confidence=0.0)
