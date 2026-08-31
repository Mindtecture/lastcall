"""Semantic wish-list matching with Gemini Flash-Lite.

One model call judges the new offer against ALL customer wish lists at once
(a handful of demo customers — a single cheap call). Wish lists are free
text ("sushi under $15"), so price caps and paraphrases match naturally.
Falls back to the full Flash model if Lite is unavailable in the region.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import types
from pydantic import BaseModel

from agents import config as agent_config

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _genai_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=agent_config.GCP_PROJECT_ID,
            location=agent_config.VERTEX_LOCATION,
        )
    return _client


class Match(BaseModel):
    customer_id: str
    wish: str  # the wish-list entry that matched, verbatim


class MatchResult(BaseModel):
    matches: list[Match]


PROMPT = """You match a new offer from a local business against customer wish lists.

THE OFFER:
{offer}

THE CUSTOMERS (id + wish list entries):
{customers}

A customer matches if ANY of their wish-list entries plausibly describes this offer,
including any price condition (e.g. "sushi under $15" only matches sushi priced below
$15 per unit). Be strict about the item category, lenient about wording.
Return every matching customer with the wish-list entry that matched.
Return an empty list if nobody matches."""


def match_offer(offer: dict, customers: list[dict]) -> list[Match]:
    """Return the customers whose wish lists match this offer."""
    if not customers:
        return []
    offer_desc = (
        f'{offer["qty_total"]}x "{offer["item_label"]}" '
        f'(tags: {", ".join(offer.get("tags") or []) or "none"}) '
        f'at ${offer["offer_price"] / 100:.2f} per unit, '
        f'pickup until {offer.get("expiry_label", "?")}'
    )
    cust_desc = "\n".join(
        f'- {c["id"]}: {"; ".join(c.get("wishlist") or [])}' for c in customers
    )
    prompt = PROMPT.format(offer=offer_desc, customers=cust_desc)

    for model in (agent_config.GEMINI_MODEL_LITE, agent_config.GEMINI_MODEL):
        try:
            resp = _genai_client().models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=MatchResult,
                ),
            )
            result: MatchResult = resp.parsed
            valid_ids = {c["id"] for c in customers}
            return [m for m in result.matches if m.customer_id in valid_ids]
        except Exception as exc:  # noqa: BLE001 — model fallback, then give up
            logger.warning("matching with %s failed: %s", model, exc)
    return []
