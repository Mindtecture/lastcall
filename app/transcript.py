"""Render the `messages` collection as a clean chat transcript.

    python -m app.transcript          # last 50 messages
    python -m app.transcript 200      # last 200

This is the demo-video fallback: if live WhatsApp is unavailable, the stub
run's transcript IS the conversation, direction + timestamps included.
"""

from __future__ import annotations

import sys
from zoneinfo import ZoneInfo

from app import config, db


def _names_by_phone() -> dict[str, str]:
    names: dict[str, list[str]] = {}
    c = db.client()
    for d in c.collection("businesses").stream():
        data = d.to_dict()
        names.setdefault(data["whatsapp_number"], []).append(data["name"])
    for d in c.collection("customers").stream():
        data = d.to_dict()
        names.setdefault(data["whatsapp_number"], []).append(data["display_name"])
    return {phone: " / ".join(ns) for phone, ns in names.items()}


def render(limit: int = 50) -> None:
    docs = list(db.client().collection("messages").stream())
    docs = [{**d.to_dict()} for d in docs]
    docs = [d for d in docs if d.get("ts")]
    docs.sort(key=lambda d: d["ts"])
    docs = docs[-limit:]

    names = _names_by_phone()
    tz = ZoneInfo(config.BUSINESS_TZ)

    print(f"=== LastCall transcript — last {len(docs)} messages ===\n")
    for d in docs:
        ts = d["ts"].astimezone(tz).strftime("%H:%M:%S")
        peer = d.get("peer", "?")
        who = d.get("peer_name") or names.get(peer) or f"…{peer[-4:]}"
        status = d.get("status", "")
        if d.get("direction") == "in":
            print(f"[{ts}]  {who} → agent:")
        else:
            tag = f"  ({status})" if status != "sent" else ""
            print(f"[{ts}]  agent → {who}:{tag}")
        print(f'    "{d.get("text", "")}"\n')


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    render(n)
