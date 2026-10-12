import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Client, CommunicationLog
from app.services.event_parsing import normalize_phone
from app.services.messaging import send_and_log
from app.services.twilio_whatsapp import is_valid_request

logger = logging.getLogger(__name__)
router = APIRouter()

EMPTY_TWIML = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
OPT_OUT_WORDS = {"stop", "unsubscribe", "parar", "sair"}
OPT_IN_WORDS = {"start", "unstop", "voltar"}


def _find_client(db, phone: str) -> Client | None:
    """All businesses share one WhatsApp number, so pick the business that talked to this number last."""
    clients = db.query(Client).filter(Client.phone_number == phone).all()
    if len(clients) <= 1:
        return clients[0] if clients else None
    last_contact = dict(
        db.query(CommunicationLog.client_id, func.max(CommunicationLog.timestamp))
        .filter(CommunicationLog.client_id.in_([c.id for c in clients]))
        .group_by(CommunicationLog.client_id)
        .all()
    )
    with_history = [c for c in clients if c.id in last_contact]
    if not with_history:
        return clients[0]
    return max(with_history, key=lambda c: last_contact[c.id])


def process_inbound(params: dict) -> None:
    from app.tasks.tasks import handle_inbound_message

    db = SessionLocal()
    try:
        sid = params.get("MessageSid")
        if sid and db.query(CommunicationLog.id).filter(CommunicationLog.provider_sid == sid).first():
            return  # Twilio retried a webhook we already handled
        phone = normalize_phone(params.get("From", ""))
        client = _find_client(db, phone) if phone else None
        if not client:
            logger.info("Ignoring WhatsApp message from unknown number")
            return

        body = (params.get("Body") or "").strip()
        if not body and params.get("NumMedia", "0") != "0":
            body = "[media message]"
        log = CommunicationLog(
            business_id=client.business_id,
            client_id=client.id,
            message_body=body,
            direction="inbound",
            sender="client",
            status="received",
            provider_sid=sid,
        )
        db.add(log)
        db.commit()

        keyword = body.casefold()
        if keyword in OPT_OUT_WORDS:
            client.opted_out = True
            db.commit()
            send_and_log(db, client, "You won't receive any more messages from us. Reply START to opt back in.", sender="system")
            return
        if keyword in OPT_IN_WORDS and client.opted_out:
            client.opted_out = False
            db.commit()
            send_and_log(db, client, "You're subscribed again. How can we help?", sender="system")
            return
        if not client.ai_paused and not client.opted_out:
            handle_inbound_message.delay(log.id)
    finally:
        db.close()


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    params = {key: value for key, value in form.items() if isinstance(value, str)}
    # Twilio signs the exact public URL it called, which differs from request.url behind a proxy
    url = settings.PUBLIC_BASE_URL.rstrip("/") + request.url.path
    if request.url.query:
        url += f"?{request.url.query}"
    if not is_valid_request(url, params, request.headers.get("X-Twilio-Signature")):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    await run_in_threadpool(process_inbound, params)
    return Response(content=EMPTY_TWIML, media_type="application/xml")
