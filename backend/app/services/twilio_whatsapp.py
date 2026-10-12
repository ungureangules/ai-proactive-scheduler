from twilio.rest import Client
from app.core.config import settings

class TwilioWhatsAppService:
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"

    def send_message(self, to_number: str, body: str):
        message = self.client.messages.create(
            from_=self.from_number,
            body=body,
            to=f"whatsapp:{to_number}"
        )
        return message.sid
