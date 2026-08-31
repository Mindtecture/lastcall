"""Firestore access layer.

Collections (design.md §4, trimmed to today's scope):
    businesses/{id}   customers/{id}   offers/{id}
    messages/{id}     — every inbound/outbound message, direction + timestamps
    agent_steps/{id}  — live agent step log (the GCP-console demo centerpiece)
    pending/{phone}   — one open clarifying question per business phone
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from google.cloud import firestore

from app import config

logger = logging.getLogger(__name__)

_client: firestore.Client | None = None


def client() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client(project=config.GCP_PROJECT_ID)
    return _client


def now() -> datetime:
    return datetime.now(timezone.utc)


# --- lookups -------------------------------------------------------------


def business_by_phone(phone: str) -> dict | None:
    docs = list(
        client()
        .collection("businesses")
        .where(filter=firestore.FieldFilter("whatsapp_number", "==", phone))
        .limit(1)
        .stream()
    )
    return {"id": docs[0].id, **docs[0].to_dict()} if docs else None


def customer_by_phone(phone: str) -> dict | None:
    docs = list(
        client()
        .collection("customers")
        .where(filter=firestore.FieldFilter("whatsapp_number", "==", phone))
        .limit(1)
        .stream()
    )
    return {"id": docs[0].id, **docs[0].to_dict()} if docs else None


def business_by_id(business_id: str) -> dict | None:
    snap = client().collection("businesses").document(business_id).get()
    return {"id": snap.id, **snap.to_dict()} if snap.exists else None


def all_customers() -> list[dict]:
    return [{"id": d.id, **d.to_dict()} for d in client().collection("customers").stream()]


def offers_notified_to(customer_id: str) -> list[dict]:
    """Offers this customer was notified about, newest first (client-side sort
    to avoid a composite index)."""
    docs = (
        client()
        .collection("offers")
        .where(
            filter=firestore.FieldFilter(
                "notified_customer_ids", "array_contains", customer_id
            )
        )
        .stream()
    )
    offers = [{"id": d.id, **d.to_dict()} for d in docs]
    offers.sort(key=lambda o: o.get("created_at") or now(), reverse=True)
    return offers


# --- message log ---------------------------------------------------------


def log_message(
    direction: str,  # "in" | "out"
    peer: str,  # the WhatsApp number on the other side
    text: str,
    status: str,  # "received" | "sent" | "stub" | "failed"
    *,
    wa_message_id: str | None = None,
    run_id: str | None = None,
    peer_name: str | None = None,
) -> None:
    doc = {
        "direction": direction,
        "peer": peer,
        "peer_name": peer_name,
        "text": text,
        "status": status,
        "wa_message_id": wa_message_id,
        "run_id": run_id,
        "ts": firestore.SERVER_TIMESTAMP,
        "logged_at_iso": now().isoformat(),
    }
    client().collection("messages").add(doc)


def seen_wa_message(wa_message_id: str) -> bool:
    """Idempotency for Meta webhook retries: True if already processed."""
    ref = client().collection("processed_messages").document(wa_message_id)
    if ref.get().exists:
        return True
    ref.set({"ts": firestore.SERVER_TIMESTAMP})
    return False


# --- agent step log ------------------------------------------------------


def log_step(
    run_id: str,
    step: str,
    detail: str,
    *,
    business_id: str | None = None,
    offer_id: str | None = None,
) -> None:
    client().collection("agent_steps").add(
        {
            "run_id": run_id,
            "step": step,
            "detail": detail,
            "business_id": business_id,
            "offer_id": offer_id,
            "ts": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info("[%s] %s: %s", run_id, step, detail)


# --- pending clarification (one per business phone) ----------------------


def get_pending(phone: str) -> dict | None:
    snap = client().collection("pending").document(phone).get()
    return snap.to_dict() if snap.exists else None


def set_pending(phone: str, data: dict) -> None:
    data = {**data, "created_at": firestore.SERVER_TIMESTAMP}
    client().collection("pending").document(phone).set(data)


def clear_pending(phone: str) -> None:
    client().collection("pending").document(phone).delete()
