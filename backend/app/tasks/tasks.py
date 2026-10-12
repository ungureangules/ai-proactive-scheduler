from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.scheduler_logic import SchedulerService
from app.services.twilio_whatsapp import TwilioWhatsAppService
from app.models.models import Business, Client

@celery_app.task
def run_daily_outreach():
    db = SessionLocal()
    try:
        businesses = db.query(Business).all()
        for business in businesses:
            # 1. Sync and analyze frequency
            SchedulerService.sync_and_analyze_frequency(db, business.id)
            
            # 2. Get due clients
            due_clients = SchedulerService.get_due_clients(db, business.id)
            
            # 3. Proactively outreach
            twilio_service = TwilioWhatsAppService()
            for client in due_clients:
                # Basic proactive message
                message = f"Hi {client.name}! It's been about {client.avg_frequency_days} days since your last visit. Would you like to schedule an appointment for next Friday at 5 PM?"
                twilio_service.send_message(client.phone_number, message)
                
                # Log the outbound message
                # (Logic to log to CommunicationLog)
        
        db.commit()
    finally:
        db.close()
