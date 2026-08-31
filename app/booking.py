"""First-YES-wins booking, enforced with a Firestore transaction.

The transaction re-reads the offer inside the commit window, so two
simultaneous YESes can never both win: exactly one commit flips the offer
to `taken`, the other observes it and reports `gone`.
"""

from __future__ import annotations

import random

from google.cloud import firestore

from app import db


def try_book(offer_id: str, customer_id: str) -> dict:
    """Atomically claim an offer for a customer.

    Returns {"outcome": "won" | "already_yours" | "gone" | "unavailable",
             "code": str | None, "offer": dict | None}.
    """
    client = db.client()
    ref = client.collection("offers").document(offer_id)
    transaction = client.transaction()

    @firestore.transactional
    def _claim(txn: firestore.Transaction) -> dict:
        snap = ref.get(transaction=txn)
        if not snap.exists:
            return {"outcome": "unavailable", "code": None, "offer": None}
        offer = {"id": snap.id, **snap.to_dict()}

        if offer["status"] == "taken":
            if offer.get("winner_customer_id") == customer_id:
                return {
                    "outcome": "already_yours",
                    "code": offer.get("confirmation_code"),
                    "offer": offer,
                }
            return {"outcome": "gone", "code": None, "offer": offer}

        if offer["status"] != "published":
            return {"outcome": "unavailable", "code": None, "offer": offer}

        code = f"{random.randint(0, 9999):04d}"
        txn.update(
            ref,
            {
                "status": "taken",
                "winner_customer_id": customer_id,
                "confirmation_code": code,
                "taken_at": firestore.SERVER_TIMESTAMP,
            },
        )
        offer.update(
            status="taken", winner_customer_id=customer_id, confirmation_code=code
        )
        return {"outcome": "won", "code": code, "offer": offer}

    return _claim(transaction)
