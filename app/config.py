"""App-level configuration: WhatsApp Cloud API + runtime settings.

Vertex AI / Gemini settings live in `agents.config` (imported wherever the
models are used). This module owns everything the webhook and messaging
adapter need. `.env` at the repo root is the single local source of truth.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from dotenv import load_dotenv


def norm_phone(value: str) -> str:
    """Meta sends sender ids digits-only; store and compare them that way."""
    return re.sub(r"\D", "", value or "")

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# --- Meta WhatsApp Cloud API ---
WHATSAPP_ACCESS_TOKEN: str = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID: str = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_VERSION: str = os.environ.get("WHATSAPP_API_VERSION", "v21.0")
WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
WHATSAPP_TEST_RECIPIENT: str = norm_phone(os.environ.get("WHATSAPP_TEST_RECIPIENT", ""))

# Stub mode: outbound messages are written to Firestore `messages` only,
# never sent to Meta. The demo fallback transcript is rendered from there.
WHATSAPP_STUB: bool = os.environ.get("WHATSAPP_STUB", "0") == "1"

# Business-local timezone for expiry times like "21:00".
BUSINESS_TZ: str = os.environ.get("BUSINESS_TZ", "Asia/Beirut")

GCP_PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID", "lastcall-hackathon")
