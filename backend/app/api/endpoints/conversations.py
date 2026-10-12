from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.api.endpoints.clients import get_client_or_404
from app.api.serializers import client_out
from app.db.session import get_db
from app.models.models import Business, CommunicationLog
from app.schemas.schemas import ConversationOut, MessageIn, MessageOut
from app.services.availability import as_utc
from app.services.messaging import send_and_log

router = APIRouter()


@router.get("/", response_model=list[ConversationOut])
def list_conversations(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    latest_ids = (
        db.query(func.max(CommunicationLog.id))
        .filter(CommunicationLog.business_id == business.id, CommunicationLog.sender != "system")
        .group_by(CommunicationLog.client_id)
    )
    last_inbound = dict(
        db.query(CommunicationLog.client_id, func.max(CommunicationLog.timestamp))
        .filter(CommunicationLog.business_id == business.id, CommunicationLog.direction == "inbound")
        .group_by(CommunicationLog.client_id)
        .all()
    )
    logs = (
        db.query(CommunicationLog)
        .filter(CommunicationLog.id.in_(latest_ids))
        .order_by(CommunicationLog.timestamp.desc())
        .all()
    )
    now = datetime.now(timezone.utc)
    result = []
    for log in logs:
        client = log.client
        inbound_at = last_inbound.get(client.id)
        unread = bool(inbound_at) and (
            client.staff_last_read_at is None or as_utc(inbound_at) > as_utc(client.staff_last_read_at)
        )
        result.append(
            ConversationOut(
                client_id=client.id,
                client_name=client.name,
                phone_number=client.phone_number,
                last_message=log.message_body,
                last_message_at=as_utc(log.timestamp),
                unread=unread,
                status=client_out(client, now).status,
                ai_paused=client.ai_paused,
            )
        )
    return result


@router.get("/{client_id}/messages", response_model=list[MessageOut])
def list_messages(client_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    client = get_client_or_404(db, business, client_id)
    logs = (
        db.query(CommunicationLog)
        .filter(CommunicationLog.client_id == client.id)
        .order_by(CommunicationLog.timestamp, CommunicationLog.id)
        .all()
    )
    return [MessageOut.model_validate(log).model_copy(update={"timestamp": as_utc(log.timestamp)}) for log in logs]


@router.post("/{client_id}/read", status_code=204)
def mark_read(client_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    client = get_client_or_404(db, business, client_id)
    client.staff_last_read_at = datetime.now(timezone.utc)
    db.commit()


@router.post("/{client_id}/messages", response_model=MessageOut, status_code=201)
def send_message(client_id: int, data: MessageIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    """Staff reply. Sending manually takes over the conversation (pauses the AI)."""
    client = get_client_or_404(db, business, client_id)
    if not client.phone_number:
        raise HTTPException(status_code=400, detail="This client has no phone number")
    if client.opted_out:
        raise HTTPException(status_code=400, detail="This client opted out of messages")
    client.ai_paused = True
    log = send_and_log(db, client, data.body, sender="staff")
    if log.status == "failed":
        raise HTTPException(status_code=502, detail=f"WhatsApp message failed: {log.error}")
    return MessageOut.model_validate(log)


@router.post("/{client_id}/pause", status_code=204)
def pause_ai(client_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    get_client_or_404(db, business, client_id).ai_paused = True
    db.commit()


@router.post("/{client_id}/resume", status_code=204)
def resume_ai(client_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    get_client_or_404(db, business, client_id).ai_paused = False
    db.commit()
