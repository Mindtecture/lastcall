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
    # Warm-up doc: keeps agent_steps visible in the Firestore console's root
    # panel after a wipe, so the demo can click into it before recording.
    db.log_step("reset", "reset", "demo starting")
    print("Reset complete — businesses/customers kept; agent_steps warm-up doc written.")


if __name__ == "__main__":
    main()
