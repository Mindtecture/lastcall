"""Parse agent: one inbound WhatsApp text -> strict JSON (design.md §5).

Built with Google ADK; Gemini is served through Vertex AI using Application
Default Credentials. The agent is a pure classifier/extractor — pricing is a
separate step and is deliberately NOT done here.

Usage (programmatic):

    from agents.parse_agent import parse_message
    result = parse_message("12 salads left, close at 9")   # -> ParseResult
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import ValidationError

from agents import config
from agents.contract import CONFIDENCE_THRESHOLD, ParseResult
from agents.tags import tag_list_for_prompt

logger = logging.getLogger(__name__)

APP_NAME = "lastcall"
AGENT_NAME = "parse_agent"
MAX_ATTEMPTS = 2  # one try + one retry on invalid output

INSTRUCTION = f"""You are the parse agent for LastCall, a last-minute food offers marketplace.
Businesses text you on WhatsApp in free language. Each message is ONE of these intents:

1. "new_offer"   - the business announces surplus items to sell now.
                   Examples: "12 salads left, close at 9", "pizza margherita 5 pieces, 4 each, until 8pm",
                   "3 tiramisu portions, closing 22:00".
2. "approve"     - the business accepts the draft offer it was sent.
                   Examples: "YES", "yes", "ok", "go", "publish", "confirm", "go ahead", "sounds good".
3. "revise"      - the business changes something about the draft (price, quantity or deadline).
                   Examples: "make it 7" (price 7), "7 each", "only 5 left", "until 10", "change price to 5.50".
4. "pickup_code" - the message is essentially a 4-digit pickup code, e.g. "4821" or "code 4821".
5. "wishlist_add" - a customer asks to be told when something becomes available or wants deals.
                   Examples: "let me know when there's pizza", "I want dessert deals under 5",
                   "ping me for sushi under 15", "looking for a gym day pass".
                   This is a REQUEST for future offers — unlike new_offer, which is a seller
                   announcing stock to sell now (quantities, prices, closing times).
6. "unknown"     - anything else: greetings, questions, chit-chat, unclear or incomplete messages.

Return ONLY a JSON object with exactly these fields:
- intent: one of "new_offer", "approve", "revise", "pickup_code", "unknown"
- item_label: short item name in the business's own words (e.g. "salads", "pizza margherita");
        null unless intent is new_offer
- tags: list of tags describing the item, chosen ONLY from this fixed list: {tag_list_for_prompt()}.
        Use 1-3 tags, most specific first. Empty list if no item is mentioned or nothing fits.
- qty: number of units as an integer; null if not stated
- explicit_price: the per-unit price the business stated, as a number in currency units
        (e.g. "4 each" -> 4, "5.50" -> 5.5); null if no price is stated. Do NOT invent or compute prices.
- expiry_time: pickup deadline as 24-hour "HH:MM" (e.g. "21:00"); null if not stated.
        Hours without am/pm from 1 to 11 mean the evening (e.g. "close at 9" -> "21:00", "until 8" -> "20:00").
- code: the 4-digit pickup code as a string, only for pickup_code; otherwise null
- wish: only for wishlist_add: the want as a short phrase, "<item>" or "<item> under $X"
        (e.g. "let me know when there's pizza" -> "pizza",
        "I want dessert deals under 5" -> "dessert under $5"). Otherwise null.
- confidence: your confidence in the classification, from 0.0 to 1.0

Rules:
- For "revise", fill only the field(s) being changed. A bare number ("make it 7") is a new PRICE,
  unless the words clearly indicate a quantity ("7 pieces", "7 left") or a time ("until 7").
- For "approve" and "pickup_code", item fields are null and tags is [].
- For "wishlist_add", fill wish (and tags if something from the list fits); item_label,
  qty, explicit_price and expiry_time stay null. If you cannot tell WHAT they want,
  use "unknown" instead — never invent a wish.
- If the message is not clearly one of the intents, use "unknown" with confidence below {CONFIDENCE_THRESHOLD}.
  Never guess a new_offer from an unclear message.
- Output strictly valid JSON, no markdown, no commentary.
"""

parse_agent = LlmAgent(
    name=AGENT_NAME,
    model=config.GEMINI_MODEL,
    description=(
        "Classifies an inbound business WhatsApp message and extracts offer "
        "fields as strict JSON."
    ),
    instruction=INSTRUCTION,
    output_schema=ParseResult,
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
)

app = App(name=APP_NAME, root_agent=parse_agent)
_runner = InMemoryRunner(app=app)

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


async def _call_agent(text: str) -> str:
    """Run one stateless turn (fresh session) and return the agent's final text."""
    session = await _runner.session_service.create_session(
        app_name=APP_NAME, user_id="whatsapp", session_id=uuid.uuid4().hex
    )
    message = types.Content(role="user", parts=[types.Part.from_text(text=text)])
    final_text = ""
    async for event in _runner.run_async(
        user_id="whatsapp", session_id=session.id, new_message=message
    ):
        if event.author != AGENT_NAME or not event.content or not event.content.parts:
            continue
        chunk = "".join(
            p.text for p in event.content.parts if p.text and not p.thought
        )
        if event.is_final_response() and chunk:
            final_text = chunk
    return final_text


def _validate(raw: str) -> ParseResult:
    cleaned = _FENCE_RE.sub("", raw.strip())
    return ParseResult.model_validate_json(cleaned)


async def parse_message_async(text: str) -> ParseResult:
    """Parse one inbound message. Never raises on bad model output."""
    if not text or not text.strip():
        return ParseResult.unknown()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = await _call_agent(text)
        try:
            return _validate(raw).gated()
        except (ValidationError, ValueError) as exc:
            logger.warning(
                "parse attempt %d/%d returned invalid output (%s): %r",
                attempt,
                MAX_ATTEMPTS,
                exc.__class__.__name__,
                raw[:200],
            )
    return ParseResult.unknown()


def parse_message(text: str) -> ParseResult:
    """Synchronous convenience wrapper around `parse_message_async`."""
    return asyncio.run(parse_message_async(text))
