from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import CommunicationLog, Client, Business
from app.services.ai_agent import AIAgentService
from app.services.twilio_whatsapp import TwilioWhatsAppService
from datetime import datetime

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    form_data = await request.form()
    from_number = form_data.get("From", "").replace("whatsapp:", "")
    body = form_data.get("Body", "")
    
    # Find client by phone number
    client = db.query(Client).filter(Client.phone_number == from_number).first()
    if not client:
        return {"status": "ignored", "reason": "Client not found"}

    # Log the inbound message
    log_in = CommunicationLog(
        client_id=client.id,
        message_body=body,
        direction="inbound",
        timestamp=datetime.utcnow()
    )
    db.add(log_in)
    
    # Fetch chat history
    history_logs = db.query(CommunicationLog).filter(CommunicationLog.client_id == client.id).order_by(CommunicationLog.timestamp.desc()).limit(10).all()
    # Convert logs to format AIAgentService expects (this is simplified)
    chat_history = [] # TODO: Map logs to Human/AI messages
    
    # Process with AI
    ai_service = AIAgentService(business_id=client.business_id, db_session=db)
    ai_response = ai_service.process_message(client_id=client.id, message_body=body, chat_history=chat_history)
    
    # Send response via Twilio
    twilio_service = TwilioWhatsAppService()
    twilio_service.send_message(to_number=client.phone_number, body=ai_response)
    
    # Log the outbound message
    log_out = CommunicationLog(
        client_id=client.id,
        message_body=ai_response,
        direction="outbound",
        timestamp=datetime.utcnow()
    )
    db.add(log_out)
    db.commit()
    
    return {"status": "success"}
