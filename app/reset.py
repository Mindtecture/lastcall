"""Clear demo state (offers, messages, agent_steps, pending, processed) — NOT
the seeded businesses/customers. Run before recording the demo for a clean slate.

    python -m app.reset
"""

from __future__ import annotations

from app import db

COLLECTIONS = ("offers", "messages", "agent_steps", "pending", "processed_messages")


def main() -> None:
    c = db.client()
    for col in COLLECTIONS:
        n = 0
        for d in c.collection(col).stream():
            d.reference.delete()
            n += 1
        print(f"{col}: {n} deleted")
    print("Reset complete — businesses/customers kept.")


if __name__ == "__main__":
    main()
