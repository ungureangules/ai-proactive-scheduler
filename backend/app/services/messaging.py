from sqlalchemy.orm import Session

from app.models.models import Client, CommunicationLog
from app.services.twilio_whatsapp import MessageSendError, TwilioWhatsAppService


def send_and_log(
    db: Session,
    client: Client,
    body: str,
    sender: str,
    template: tuple[str, dict[str, str]] | None = None,
) -> CommunicationLog:
    """Send a WhatsApp message to `client` and record it, including failures. Commits."""
    log = CommunicationLog(
        business_id=client.business_id,
        client_id=client.id,
        message_body=body,
        direction="outbound",
        sender=sender,
    )
    try:
        twilio = TwilioWhatsAppService()
        if template:
            log.provider_sid = twilio.send_template(client.phone_number, *template)
        else:
            log.provider_sid = twilio.send_message(client.phone_number, body)
        log.status = "sent"
    except MessageSendError as exc:
        log.status = "failed"
        log.error = str(exc)
    db.add(log)
    db.commit()
    return log
