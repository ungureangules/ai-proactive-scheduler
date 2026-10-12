import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Business, Client, CommunicationLog
from app.services.ai_agent import AIAgentService
from app.services.availability import as_utc
from app.services.messaging import send_and_log
from app.services.scheduler_logic import SchedulerService
from app.services.twilio_whatsapp import is_configured

logger = logging.getLogger(__name__)

HANDOFF_REPLY = "Thanks! Someone from our team will reply to you shortly."


def outreach_text(client: Client, business: Business, days: int) -> str:
    return (
        f"Hi {client.name}! It's been about {days} days since your last visit to {business.name}. "
        "Would you like to book your next appointment? Just reply here and we'll find a time that suits you."
    )


@celery_app.task
def run_outreach_cycle():
    db = SessionLocal()
    try:
        business_ids = [b.id for b in db.query(Business.id).all()]
    finally:
        db.close()
    for business_id in business_ids:
        process_business.delay(business_id)


@celery_app.task
def process_business(business_id: int):
    db = SessionLocal()
    try:
        business = db.get(Business, business_id)
        if not business:
            return
        if business.google_credentials_encrypted:
            try:
                SchedulerService.sync_and_analyze_frequency(db, business.id)
            except Exception:
                db.rollback()
                logger.exception("Calendar sync failed for business %s", business.id)

        local_now = datetime.now(ZoneInfo(business.timezone))
        today = local_now.date().isoformat()
        if (
            business.outreach_enabled
            and local_now.hour == settings.OUTREACH_LOCAL_HOUR
            and business.last_outreach_run_on != today
        ):
            business.last_outreach_run_on = today
            db.commit()
            run_outreach(db, business)
    finally:
        db.close()


def run_outreach(db, business: Business) -> int:
    if not is_configured():
        logger.warning("Twilio not configured; skipping outreach for business %s", business.id)
        return 0
    now = datetime.now(timezone.utc)
    sent = 0
    for client in SchedulerService.get_due_clients(db, business.id, now):
        try:
            last_visit = max(as_utc(a.start_time) for a in client.appointments if a.status == "confirmed")
            days = (now - last_visit).days
            text = outreach_text(client, business, days)
            template = None
            if settings.TWILIO_OUTREACH_CONTENT_SID:
                template = (settings.TWILIO_OUTREACH_CONTENT_SID, {"1": client.name, "2": business.name, "3": str(days)})
            log = send_and_log(db, client, text, sender="ai", template=template)
            if log.status == "sent":
                client.last_outreach_at = now
                client.conversation_status = "negotiating"
                db.commit()
                sent += 1
            else:
                logger.warning("Outreach to client %s failed: %s", client.id, log.error)
        except Exception:
            db.rollback()
            logger.exception("Outreach failed for client %s", client.id)
    return sent


@celery_app.task
def handle_inbound_message(log_id: int):
    db = SessionLocal()
    try:
        log = db.get(CommunicationLog, log_id)
        if not log:
            return
        client = log.client
        if client.ai_paused or client.opted_out:
            return
        # Several quick messages in a row get one answer, from the task for the latest one
        newer = (
            db.query(CommunicationLog.id)
            .filter(
                CommunicationLog.client_id == client.id,
                CommunicationLog.id > log.id,
                CommunicationLog.sender.in_(["client", "ai", "staff"]),
            )
            .first()
        )
        if newer:
            return

        agent = AIAgentService(db, client.business, client)
        try:
            reply = agent.reply()
        except Exception as exc:
            db.rollback()
            logger.exception("AI reply failed for client %s", client.id)
            client.ai_paused = True
            db.add(
                CommunicationLog(
                    business_id=client.business_id,
                    client_id=client.id,
                    message_body=f"AI could not reply ({type(exc).__name__}); paused for staff to take over.",
                    direction="outbound",
                    sender="system",
                )
            )
            db.commit()
            return

        if agent.handed_off and not reply:
            reply = HANDOFF_REPLY
        if reply:
            if client.conversation_status == "idle":
                client.conversation_status = "negotiating"
            send_and_log(db, client, reply, sender="ai")
    finally:
        db.close()
