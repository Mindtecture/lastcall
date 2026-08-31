"""Seed demo businesses and customers.  Idempotent — fixed doc ids, safe to re-run.

    python -m app.seed

Three-phone demo setup: WHATSAPP_TEST_RECIPIENT is the business "Sunset Deli"
only; Maya and Raffi are real verified test recipients (their numbers below).
The remaining customers have fictional numbers — their notifications land in
the `messages` log only.
"""

from __future__ import annotations

import os

from app import config, db


def _mask(phone: str) -> str:
    return f"…{phone[-4:]}" if len(phone) >= 4 else phone


def seed() -> None:
    if not config.WHATSAPP_TEST_RECIPIENT:
        raise SystemExit("WHATSAPP_TEST_RECIPIENT is not set in .env")

    businesses = {
        "sunset-deli": {
            "name": "Sunset Deli",
            "whatsapp_number": config.WHATSAPP_TEST_RECIPIENT,
            "auto_publish": True,
            "rules": {"min_price": 200, "max_discount_pct": 70, "currency": "USD"},
            "location": {"lat": 33.8938, "lng": 35.5018, "area_label": "Beirut"},
        },
        "jounieh-bay-hotel": {
            "name": "Jounieh Bay Hotel",
            "whatsapp_number": "96170000099",
            "auto_publish": True,
            "rules": {"min_price": 3000, "max_discount_pct": 60, "currency": "USD"},
            "location": {"lat": 33.9808, "lng": 35.6178, "area_label": "Jounieh"},
        },
    }
    # Real verified recipient numbers come from .env (never committed);
    # the defaults are fictional so the public repo carries no real numbers.
    maya_phone = config.norm_phone(
        os.environ.get("DEMO_CUSTOMER_MAYA", "96170000001")
    )
    raffi_phone = config.norm_phone(
        os.environ.get("DEMO_CUSTOMER_RAFFI", "96170000002")
    )
    customers = {
        "cust-maya": {
            "display_name": "Maya",
            "whatsapp_number": maya_phone,
            "wishlist": ["fresh salads under $10", "sushi under $15"],
        },
        "cust-raffi": {
            "display_name": "Raffi",
            "whatsapp_number": raffi_phone,
            "wishlist": ["salad any price", "hotel night in Jounieh under $80"],
        },
        "cust-lina": {
            "display_name": "Lina",
            "whatsapp_number": "96170000003",
            "wishlist": ["gym day pass", "vegan food under $8"],
        },
        "cust-karim": {
            "display_name": "Karim",
            "whatsapp_number": "96170000004",
            "wishlist": ["pizza or burgers under $8"],
        },
    }

    c = db.client()
    for doc_id, data in businesses.items():
        c.collection("businesses").document(doc_id).set(data)
        print(f"business {doc_id}: {data['name']} ({_mask(data['whatsapp_number'])})")
    for doc_id, data in customers.items():
        c.collection("customers").document(doc_id).set(data)
        print(
            f"customer {doc_id}: {data['display_name']} "
            f"({_mask(data['whatsapp_number'])}) — {'; '.join(data['wishlist'])}"
        )
    print("Seed complete.")


if __name__ == "__main__":
    seed()
