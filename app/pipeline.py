"""The agent pipeline: route -> parse -> clarify -> price -> publish -> match -> notify -> book.

One inbound WhatsApp message enters `handle_inbound`; every outbound reply
goes through `app.wa` (real or stub) and every decision is written to the
`agent_steps` collection — the live log shown in the GCP console demo.

Clarification rule (strict): if MORE THAN ONE essential field is missing,
they are asked for in a SINGLE message. There is never a second question —
if the answer still leaves gaps, the agent asks to resend the whole offer.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.cloud import firestore

from agents.parse_agent import parse_message_async
from app import config, db, wa
from app.booking import try_book
from app.matching import match_offer

logger = logging.getLogger(__name__)

YES_WORDS = {
    "yes", "y", "yes!", "yes.", "yess", "yep", "yeah", "yes please",
    "book", "book it", "i'll take it", "take it",
}

ESSENTIALS = ("item_label", "qty", "price_cents", "expiry_time")
QUESTION_BITS = {
    "item_label": "what's the item",
    "qty": "how many do you have",
    "price_cents": "at what price each",
    "expiry_time": "until what time",
}

EXAMPLE = "12 salads at $4 until 21:00"


def _is_yes(text: str) -> bool:
    return text.strip().lower().rstrip("!.") in YES_WORDS or (
        text.strip().lower().startswith("yes ")
    )


def _price(cents: int) -> str:
    return f"${cents / 100:.2f}"


def _draft_from(result) -> dict:
    """Non-null offer fields from a ParseResult (new_offer or revise alike)."""
    d: dict = {}
    if result.item_label:
        d["item_label"] = result.item_label
    if result.tags:
        d["tags"] = list(result.tags)
    if result.qty:
        d["qty"] = result.qty
    if result.explicit_price is not None and result.explicit_price > 0:
        d["price_cents"] = round(result.explicit_price * 100)
    if result.expiry_time:
        d["expiry_time"] = result.expiry_time
    return d


def _missing(draft: dict) -> list[str]:
    return [f for f in ESSENTIALS if not draft.get(f)]


def _clarify_question(missing: list[str]) -> str:
    bits = [QUESTION_BITS[f] for f in missing]
    if len(bits) == 1:
        q = bits[0]
    else:
        q = ", ".join(bits[:-1]) + " and " + bits[-1]
    return f"Quick question — {q}?"


def _expires_at(expiry_time: str) -> datetime:
    """'21:00' -> the next occurrence of that local time (business timezone)."""
    tz = ZoneInfo(config.BUSINESS_TZ)
    now_local = datetime.now(tz)
    hour, minute = (int(p) for p in expiry_time.split(":"))
    exp = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if exp <= now_local:
        exp += timedelta(days=1)
    return exp


async def handle_inbound(frm: str, text: str, run_id: str) -> list[dict]:
    """Process one inbound message. Returns the outbound messages produced."""
    outbound: list[dict] = []

    def send(to: str, body: str, name: str | None = None) -> None:
        status = wa.send_text(to, body, run_id=run_id, peer_name=name)
        outbound.append({"to": to, "text": body, "status": status})

    business = db.business_by_phone(frm)
    customer = db.customer_by_phone(frm)
    pending = db.get_pending(frm)

    try:
        if business and pending:
            await _continue_clarification(business, pending, frm, text, run_id, send)
        elif customer and _is_yes(text):
            _handle_yes(customer, run_id, send)
        elif business:
            await _business_message(business, frm, text, run_id, send)
        elif customer:
            wishes = "; ".join(customer.get("wishlist") or [])
            send(
                frm,
                f"Hi {customer.get('display_name', '')}! I watch last-minute offers "
                f"for you (wish list: {wishes}). I'll message you when something "
                f"matches — reply YES then to book it.",
                customer.get("display_name"),
            )
        else:
            send(
                frm,
                "Hi, this is LastCall! Businesses: text your surplus, "
                f"e.g. '{EXAMPLE}'. Customers: you need a wish list on file.",
            )
    except Exception:
        logger.exception("pipeline failed for run %s", run_id)
        db.log_step(run_id, "error", "pipeline error — see service logs")
        send(frm, "Something went wrong on my side — please try again in a minute.")
    return outbound


# --- business side -------------------------------------------------------


async def _business_message(business, frm, text, run_id, send) -> None:
    result = await parse_message_async(text)
    db.log_step(
        run_id,
        "parse",
        f'"{text}" -> intent={result.intent} conf={result.confidence:.2f}',
        business_id=business["id"],
    )

    if result.intent == "new_offer":
        draft = _draft_from(result)
        missing = _missing(draft)
        if missing:
            db.set_pending(
                frm,
                {"business_id": business["id"], "draft": draft, "source_message": text},
            )
            question = _clarify_question(missing)
            db.log_step(
                run_id,
                "clarify",
                f"missing {', '.join(missing)} -> asked in one message",
                business_id=business["id"],
            )
            item = draft.get("item_label")
            prefix = f"Got it — {item}. " if item else ""
            send(frm, prefix + question, business["name"])
        else:
            _publish_and_match(business, draft, text, run_id, send)
    else:
        send(
            frm,
            f"Sorry, I didn't catch that. Text your surplus like: '{EXAMPLE}'.",
            business["name"],
        )


async def _continue_clarification(business, pending, frm, text, run_id, send) -> None:
    result = await parse_message_async(text)
    update = _draft_from(result)
    db.log_step(
        run_id,
        "clarify",
        f'answer "{text}" -> filled {", ".join(update) or "nothing"}',
        business_id=business["id"],
    )
    draft = {**(pending.get("draft") or {}), **update}
    db.clear_pending(frm)  # one question only — never a second turn

    if _missing(draft):
        send(
            frm,
            "I still couldn't complete the offer. Please send it in one "
            f"message, e.g. '{EXAMPLE}'.",
            business["name"],
        )
        db.log_step(
            run_id,
            "clarify",
            f"still missing {', '.join(_missing(draft))} -> asked for full resend",
            business_id=business["id"],
        )
    else:
        _publish_and_match(
            business, draft, pending.get("source_message", text), run_id, send
        )


def _publish_and_match(business, draft, source_message, run_id, send) -> None:
    # 1. price within owner rules
    rules = business.get("rules") or {}
    min_price = int(rules.get("min_price", 0))
    price = int(draft["price_cents"])
    if price < min_price:
        db.log_step(
            run_id,
            "price",
            f"stated {_price(price)} is below the owner's minimum "
            f"{_price(min_price)} -> clamped up",
            business_id=business["id"],
        )
        price = min_price
    else:
        db.log_step(
            run_id,
            "price",
            f"{_price(price)} ok within owner rules (min {_price(min_price)})",
            business_id=business["id"],
        )

    # 2. publish
    expires = _expires_at(draft["expiry_time"])
    offer_doc = {
        "business_id": business["id"],
        "business_name": business["name"],
        "item_label": draft["item_label"],
        "tags": draft.get("tags") or [],
        "qty_total": draft["qty"],
        "qty_left": draft["qty"],
        "offer_price": price,
        "currency": rules.get("currency", "USD"),
        "status": "published",
        "expiry_label": draft["expiry_time"],
        "expires_at": expires,
        "created_at": firestore.SERVER_TIMESTAMP,
        "source_message": source_message,
        "notified_customer_ids": [],
        "run_id": run_id,
    }
    _, ref = db.client().collection("offers").add(offer_doc)
    db.log_step(
        run_id,
        "publish",
        f'{draft["qty"]}x {draft["item_label"]} at {_price(price)} '
        f'until {draft["expiry_time"]} -> published',
        business_id=business["id"],
        offer_id=ref.id,
    )
    send(
        business["whatsapp_number"],
        f'✅ Published: {draft["qty"]}x {draft["item_label"]} at {_price(price)}, '
        f'pickup until {draft["expiry_time"]}. Matching customers now…',
        business["name"],
    )

    # 3. match wish lists (semantic, Flash-Lite)
    customers = db.all_customers()
    offer_for_match = {**offer_doc, "id": ref.id}
    matches = match_offer(offer_for_match, customers)
    by_id = {c["id"]: c for c in customers}
    db.log_step(
        run_id,
        "match",
        f"{len(matches)} of {len(customers)} wish lists match",
        business_id=business["id"],
        offer_id=ref.id,
    )

    # 4. notify matched customers
    notified = []
    for m in matches:
        cust = by_id[m.customer_id]
        send(
            cust["whatsapp_number"],
            f'🔔 LastCall: {business["name"]} has {draft["qty"]}x '
            f'{draft["item_label"]} at {_price(price)}, pickup until '
            f'{draft["expiry_time"]} (matched your wish: "{m.wish}"). '
            f"Reply YES to book — first come, first served.",
            cust.get("display_name"),
        )
        notified.append(m.customer_id)
        db.log_step(
            run_id,
            "notify",
            f'{cust.get("display_name", m.customer_id)} notified '
            f'(wish: "{m.wish}")',
            business_id=business["id"],
            offer_id=ref.id,
        )
    if notified:
        ref.update({"notified_customer_ids": notified})
        send(
            business["whatsapp_number"],
            f"📣 {len(notified)} matched customer(s) notified.",
            business["name"],
        )
    else:
        send(
            business["whatsapp_number"],
            "No wish-list matches right now — the offer stays live.",
            business["name"],
        )


# --- customer side -------------------------------------------------------


def _handle_yes(customer, run_id, send) -> None:
    offers = db.offers_notified_to(customer["id"])
    published = [o for o in offers if o["status"] == "published"]
    name = customer.get("display_name", "")

    if not published:
        # No open offer — answer about the NEWEST one they were notified of,
        # so a late YES for the sushi isn't answered about yesterday's salads.
        newest = offers[0] if offers else None
        if newest and newest.get("winner_customer_id") == customer["id"]:
            o = newest
            send(
                customer["whatsapp_number"],
                f'You already booked it ✅ {o["item_label"]} from '
                f'{o["business_name"]}, code {o["confirmation_code"]}.',
                name,
            )
        elif offers:
            db.log_step(
                run_id,
                "book",
                f'{name or customer["id"]} said YES too late — offer already taken',
                business_id=(offers[0] or {}).get("business_id"),
                offer_id=(offers[0] or {}).get("id"),
            )
            send(
                customer["whatsapp_number"],
                "Sorry — that offer is already gone. I'll keep watching "
                "your wish list. 🤞",
                name,
            )
        else:
            send(
                customer["whatsapp_number"],
                "Nothing to book right now — I'll message you when an offer "
                "matches your wish list.",
                name,
            )
        return

    offer = published[0]
    result = try_book(offer["id"], customer["id"])
    o = result["offer"] or offer

    if result["outcome"] == "won":
        db.log_step(
            run_id,
            "book",
            f'{name or customer["id"]} booked {o["item_label"]} '
            f'(code {result["code"]}) — first YES wins',
            business_id=o["business_id"],
            offer_id=o["id"],
        )
        send(
            customer["whatsapp_number"],
            f'🎉 It\'s yours! {o["qty_total"]}x {o["item_label"]} from '
            f'{o["business_name"]} at {_price(o["offer_price"])}. '
            f'Confirmation code: {result["code"]} — show it at pickup '
            f'before {o["expiry_label"]}.',
            name,
        )
        biz = db.business_by_id(o["business_id"])
        if biz:
            send(
                biz["whatsapp_number"],
                f'📦 Booked: {name or "a customer"} took your '
                f'{o["item_label"]} offer. Confirmation code {result["code"]} — '
                f"binding, they'll show it at pickup.",
                biz["name"],
            )
    elif result["outcome"] == "already_yours":
        send(
            customer["whatsapp_number"],
            f'You already booked it ✅ Code: {result["code"]}.',
            name,
        )
    else:  # gone / unavailable — lost the race
        db.log_step(
            run_id,
            "book",
            f'{name or customer["id"]} said YES too late — offer already taken',
            business_id=o.get("business_id"),
            offer_id=o.get("id"),
        )
        send(
            customer["whatsapp_number"],
            "Sorry — that offer is already gone. I'll keep watching your "
            "wish list. 🤞",
            name,
        )
