import json

from twilio.base.exceptions import TwilioRestException
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from app.core.config import settings


class MessageSendError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_WHATSAPP_NUMBER)


def is_valid_request(url: str, params: dict, signature: str | None) -> bool:
    if not settings.TWILIO_AUTH_TOKEN or not signature:
        return False
    return RequestValidator(settings.TWILIO_AUTH_TOKEN).validate(url, params, signature)


class TwilioWhatsAppService:
    def __init__(self):
        if not is_configured():
            raise MessageSendError("Twilio is not configured")
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"

    def send_message(self, to_number: str, body: str) -> str:
        """Free-form message; WhatsApp only delivers these within 24h of the client's last message."""
        try:
            message = self.client.messages.create(from_=self.from_number, body=body, to=f"whatsapp:{to_number}")
        except TwilioRestException as exc:
            raise MessageSendError(exc.msg) from exc
        return message.sid

    def send_template(self, to_number: str, content_sid: str, variables: dict[str, str]) -> str:
        try:
            message = self.client.messages.create(
                from_=self.from_number,
                to=f"whatsapp:{to_number}",
                content_sid=content_sid,
                content_variables=json.dumps(variables),
            )
        except TwilioRestException as exc:
            raise MessageSendError(exc.msg) from exc
        return message.sid
