"""WhatsApp adapter — the ONLY place that talks to Meta.

Stub mode (WHATSAPP_STUB=1): no network call; the message is logged to the
Firestore `messages` collection exactly like a real send, with status "stub".
The demo-fallback transcript renders from that collection.

Real mode: Cloud API `messages` endpoint. A failed send (expired token,
unverified recipient, ...) is logged as "failed" and never raises — WhatsApp
is a thin adapter, never the critical path (design.md §7).
"""

from __future__ import annotations

import logging

import requests

from app import config, db

logger = logging.getLogger(__name__)


def send_text(
    to: str,
    text: str,
    *,
    run_id: str | None = None,
    peer_name: str | None = None,
) -> str:
    """Send one text message. Returns the log status: sent | stub | failed."""
    if config.WHATSAPP_STUB:
        db.log_message(
            "out", to, text, "stub", run_id=run_id, peer_name=peer_name
        )
        logger.info("STUB -> %s: %s", to, text)
        return "stub"

    url = (
        f"https://graph.facebook.com/{config.WHATSAPP_API_VERSION}"
        f"/{config.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {config.WHATSAPP_ACCESS_TOKEN}"},
            timeout=15,
        )
        if resp.ok:
            wa_id = (resp.json().get("messages") or [{}])[0].get("id")
            db.log_message(
                "out", to, text, "sent",
                wa_message_id=wa_id, run_id=run_id, peer_name=peer_name,
            )
            return "sent"
        logger.error("WhatsApp send failed (%s): %s", resp.status_code, resp.text[:300])
    except requests.RequestException as exc:
        logger.error("WhatsApp send error: %s", exc)
    db.log_message("out", to, text, "failed", run_id=run_id, peer_name=peer_name)
    return "failed"
