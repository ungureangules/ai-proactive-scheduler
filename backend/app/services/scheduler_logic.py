import collections
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Appointment, Business, Client
from app.services.availability import as_utc
from app.services.event_parsing import ParsedEvent, analyze_frequency, parse_event
from app.services.google_calendar import GoogleCalendarClient

logger = logging.getLogger(__name__)


class SchedulerService:
    @staticmethod
    def _match_client(db: Session, business: Business, parsed: ParsedEvent, by_name: dict[str, list[Client]]) -> Client | None:
        if parsed.client_id is not None:
            client = db.get(Client, parsed.client_id)
            if client and client.business_id == business.id:
                return client
        if parsed.phone_number:
            client = (
                db.query(Client)
                .filter(Client.business_id == business.id, Client.phone_number == parsed.phone_number)
                .first()
            )
            if not client:
                client = Client(business_id=business.id, name=parsed.client_name or parsed.phone_number, phone_number=parsed.phone_number)
                db.add(client)
                db.flush()
                by_name.setdefault(client.name.casefold(), []).append(client)
            return client
        # No phone in the event: link it only to an existing client with exactly this name
        matches = by_name.get(parsed.client_name.casefold(), [])
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def sync_and_analyze_frequency(db: Session, business_id: int) -> dict:
        business = db.get(Business, business_id)
        if not business or not business.google_credentials_encrypted:
            return {"synced": 0, "skipped": 0}

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=settings.SYNC_LOOKBACK_DAYS)
        window_end = now + timedelta(days=settings.SYNC_LOOKAHEAD_DAYS)
        calendar = GoogleCalendarClient(db, business)
        events = calendar.list_events(window_start, window_end)

        by_name: dict[str, list[Client]] = collections.defaultdict(list)
        for client in db.query(Client).filter(Client.business_id == business.id).all():
            by_name[client.name.casefold()].append(client)

        seen_event_ids, touched_clients = set(), set()
        synced = skipped = 0
        for event in events:
            parsed = parse_event(event, business.default_country_code)
            if not parsed:
                continue
            client = SchedulerService._match_client(db, business, parsed, by_name)
            if not client:
                skipped += 1
                continue
            seen_event_ids.add(parsed.event_id)
            touched_clients.add(client.id)
            appointment = (
                db.query(Appointment)
                .filter(Appointment.business_id == business.id, Appointment.google_event_id == parsed.event_id)
                .first()
            )
            if not appointment:
                appointment = Appointment(business_id=business.id, google_event_id=parsed.event_id, source="google")
                db.add(appointment)
            appointment.client_id = client.id
            appointment.start_time = as_utc(parsed.start)
            appointment.end_time = as_utc(parsed.end)
            appointment.service_type = parsed.service_type or appointment.service_type
            appointment.status = "confirmed"
            synced += 1

        # Events deleted from Google inside the sync window were cancelled
        stale = (
            db.query(Appointment)
            .filter(
                Appointment.business_id == business.id,
                Appointment.google_event_id.isnot(None),
                Appointment.status == "confirmed",
                Appointment.start_time >= window_start,
                Appointment.start_time <= window_end,
            )
            .all()
        )
        for appointment in stale:
            if appointment.google_event_id not in seen_event_ids:
                appointment.status = "cancelled"
                touched_clients.add(appointment.client_id)
        db.flush()

        for client_id in touched_clients:
            SchedulerService.refresh_client_stats(db, db.get(Client, client_id), now)

        business.last_synced_at = now
        db.commit()
        logger.info("Synced business %s: %s events linked, %s skipped (no client match)", business.id, synced, skipped)
        return {"synced": synced, "skipped": skipped}

    @staticmethod
    def refresh_client_stats(db: Session, client: Client, now: datetime) -> None:
        appointments = (
            db.query(Appointment)
            .filter(Appointment.client_id == client.id, Appointment.status == "confirmed")
            .order_by(Appointment.start_time)
            .all()
        )
        past = [a for a in appointments if as_utc(a.start_time) <= now]
        result = analyze_frequency([as_utc(a.start_time) for a in past])
        if result:
            client.avg_frequency_days, client.frequency_confidence = result
        if past and past[-1].service_type:
            client.last_service_type = past[-1].service_type
        has_upcoming = any(as_utc(a.start_time) > now for a in appointments)
        if client.conversation_status == "booked" and not has_upcoming:
            client.conversation_status = "idle"

    @staticmethod
    def get_due_clients(db: Session, business_id: int, now: datetime | None = None) -> list[Client]:
        now = now or datetime.now(timezone.utc)
        clients = (
            db.query(Client)
            .filter(
                Client.business_id == business_id,
                Client.avg_frequency_days.isnot(None),
                Client.phone_number.isnot(None),
                Client.ai_paused.is_(False),
                Client.opted_out.is_(False),
            )
            .all()
        )
        due_clients = []
        for client in clients:
            if client.last_outreach_at and now - as_utc(client.last_outreach_at) < timedelta(days=settings.OUTREACH_COOLDOWN_DAYS):
                continue
            confirmed = [a for a in client.appointments if a.status == "confirmed"]
            if any(as_utc(a.start_time) > now for a in confirmed):
                continue  # already booked
            past = [as_utc(a.start_time) for a in confirmed]
            if not past:
                continue
            days_since_last = (now - max(past)).days
            if days_since_last >= client.avg_frequency_days - settings.OUTREACH_LEAD_DAYS:
                due_clients.append(client)
        return due_clients

    @staticmethod
    def next_outreach_date(client: Client) -> datetime | None:
        if not client.avg_frequency_days:
            return None
        past = [as_utc(a.start_time) for a in client.appointments if a.status == "confirmed"]
        if not past:
            return None
        due = max(past) + timedelta(days=client.avg_frequency_days - settings.OUTREACH_LEAD_DAYS)
        if client.last_outreach_at:
            due = max(due, as_utc(client.last_outreach_at) + timedelta(days=settings.OUTREACH_COOLDOWN_DAYS))
        return due
