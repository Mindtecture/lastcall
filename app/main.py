"""FastAPI service: Meta WhatsApp webhook + local simulator + status dump.

Endpoints:
    GET  /webhook   — Meta verification handshake (hub.challenge echo)
    POST /webhook   — inbound WhatsApp messages (acked fast, processed in background)
    POST /simulate  — same pipeline without Meta: {"from": "...", "text": "..."}
                      guarded by the X-Verify-Token header; returns the replies
    GET  /offers    — read-only JSON dump of recent offers
    GET  /health    — liveness
"""

from __future__ import annotations

import logging
import uuid

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app import config, db, pipeline

logging.basicConfig(level=logging.INFO)
logging.getLogger("google_genai.models").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI(title="LastCall", version="0.1.0")


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


@app.get("/")
def root():
    return {"service": "lastcall", "stub_mode": config.WHATSAPP_STUB}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == config.WHATSAPP_WEBHOOK_VERIFY_TOKEN
    ):
        return PlainTextResponse(params.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request, background: BackgroundTasks):
    payload = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                wa_id = msg.get("id", "")
                frm = config.norm_phone(msg.get("from", ""))
                text = (msg.get("text") or {}).get("body", "")
                if not frm or not text:
                    continue
                if wa_id and db.seen_wa_message(wa_id):
                    logger.info("duplicate webhook delivery %s ignored", wa_id)
                    continue
                run_id = _new_run_id()
                db.log_message(
                    "in", frm, text, "received",
                    wa_message_id=wa_id, run_id=run_id,
                )
                background.add_task(pipeline.handle_inbound, frm, text, run_id)
    return {"status": "ok"}


@app.post("/simulate")
async def simulate(
    request: Request,
    x_verify_token: str = Header(default=""),
):
    """Post an inbound event directly (dev/tests/demo fallback, design.md §7)."""
    if x_verify_token != config.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="bad token")
    body = await request.json()
    frm = config.norm_phone(str(body.get("from", "")))
    text = str(body.get("text", "")).strip()
    if not frm or not text:
        raise HTTPException(status_code=422, detail="need 'from' and 'text'")
    run_id = _new_run_id()
    db.log_message("in", frm, text, "received", run_id=run_id)
    outbound = await pipeline.handle_inbound(frm, text, run_id)
    return {"run_id": run_id, "outbound": outbound}


@app.get("/offers")
def offers(limit: int = 20):
    docs = db.client().collection("offers").stream()
    items = [{"id": d.id, **d.to_dict()} for d in docs]
    items.sort(key=lambda o: str(o.get("created_at") or ""), reverse=True)
    for o in items:
        o.pop("expires_at", None)  # datetime — keep the JSON dump simple
        o["created_at"] = str(o.get("created_at"))
        o.pop("taken_at", None)
    return {"offers": items[:limit]}
