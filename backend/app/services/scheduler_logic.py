from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import Business, Client, Appointment
from app.services.google_calendar import GoogleCalendarService
import collections

class SchedulerService:
    @staticmethod
    def sync_and_analyze_frequency(db: Session, business_id: int):
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business or not business.google_oauth_token:
            return

        # Fetch past events (e.g., last 6 months)
        six_months_ago = (datetime.utcnow() - timedelta(days=180)).isoformat() + 'Z'
        service = GoogleCalendarService.get_calendar_client(business.google_oauth_token)
        events_result = service.events().list(
            calendarId='primary', timeMin=six_months_ago,
            singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # Group events by client (using summary/name for now)
        client_visits = collections.defaultdict(list)
        for event in events:
            summary = event.get('summary', 'Unknown')
            start_str = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            if start_str:
                # Handle both dateTime and date formats
                if 'T' in start_str:
                    start_dt = datetime.fromisoformat(start_str.replace('Z', ''))
                else:
                    start_dt = datetime.strptime(start_str, '%Y-%m-%d')
                client_visits[summary].append(start_dt)

        # Calculate average frequency for each client
        for name, visits in client_visits.items():
            if len(visits) < 2:
                continue
            
            visits.sort()
            gaps = [(visits[i+1] - visits[i]).days for i in range(len(visits)-1)]
            avg_gap = sum(gaps) / len(gaps)
            
            # Update or create client in DB
            client = db.query(Client).filter(Client.name == name, Client.business_id == business_id).first()
            if not client:
                client = Client(name=name, business_id=business_id)
                db.add(client)
                db.flush()
            
            client.avg_frequency_days = int(avg_gap)
            
            # Sync appointments to DB
            for visit in visits:
                existing = db.query(Appointment).filter(Appointment.client_id == client.id, Appointment.start_time == visit).first()
                if not existing:
                    app = Appointment(client_id=client.id, start_time=visit, status="confirmed")
                    db.add(app)
        
        db.commit()

    @staticmethod
    def get_due_clients(db: Session, business_id: int):
        clients = db.query(Client).filter(Client.business_id == business_id).all()
        due_clients = []
        for client in clients:
            if not client.avg_frequency_days:
                continue
            
            last_appointment = db.query(Appointment).filter(Appointment.client_id == client.id).order_by(Appointment.start_time.desc()).first()
            if not last_appointment:
                continue
            
            days_since_last = (datetime.utcnow() - last_appointment.start_time).days
            if days_since_last >= client.avg_frequency_days:
                due_clients.append(client)
        
        return due_clients
