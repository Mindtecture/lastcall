"""Environment configuration for LastCall agents.

Loads `.env` from the repo root and exposes the settings the agents need.
Also maps our own variable names onto the ones the Google GenAI SDK / ADK
read, so Gemini is served via Vertex AI with Application Default Credentials.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

GCP_PROJECT_ID: str = os.environ.get("GCP_PROJECT_ID", "")
VERTEX_LOCATION: str = os.environ.get("VERTEX_LOCATION", "europe-west1")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MODEL_LITE: str = os.environ.get("GEMINI_MODEL_LITE", "gemini-2.5-flash-lite")


def configure_vertex() -> None:
    """Point ADK / google-genai at Vertex AI using ADC (no API key)."""
    if not GCP_PROJECT_ID:
        raise RuntimeError(
            "GCP_PROJECT_ID is not set. Copy .env.example to .env and fill it in."
        )
    # Both spellings are honoured by google-genai depending on version.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", GCP_PROJECT_ID)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", VERTEX_LOCATION)


configure_vertex()
