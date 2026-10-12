from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Appointment, Business, Client
from app.services.availability import as_utc, free_slots, is_slot_free
from app.services.google_calendar import GoogleCalendarClient, GoogleNotConnected, build_event_body


class SlotUnavailable(Exception):
    pass


def _calendar(db: Session, business: Business) -> GoogleCalendarClient | None:
    try:
        return GoogleCalendarClient(db, business)
    except GoogleNotConnected:
        return None


def busy_intervals(db: Session, business: Business, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    start, end = as_utc(start), as_utc(end)
    rows = (
        db.query(Appointment)
        .filter(
            Appointment.business_id == business.id,
            Appointment.status == "confirmed",
            Appointment.start_time < end,
            Appointment.end_time > start,
        )
        .all()
    )
    busy = [(as_utc(a.start_time), as_utc(a.end_time)) for a in rows]
    calendar = _calendar(db, business)
    if calendar:
        busy.extend(calendar.busy_intervals(start, end))
    return busy


def available_slots(db: Session, business: Business, day: date, now: datetime | None = None) -> list[datetime]:
    tz = ZoneInfo(business.timezone)
    day_start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    busy = busy_intervals(db, business, day_start, day_start + timedelta(days=1))
    return free_slots(
        day,
        business.working_hours,
        business.timezone,
        business.appointment_duration_minutes,
        busy,
        now or datetime.now(timezone.utc),
        settings.MIN_BOOKING_NOTICE_MINUTES,
    )


def book_appointment(
    db: Session,
    business: Business,
    client: Client,
    start: datetime,
    service_type: str | None,
    source: str,
    check: str = "availability",
) -> Appointment:
    """Create the appointment in the DB and, when connected, in Google Calendar.

    check="availability" requires a free slot inside opening hours (used by the AI);
    check="clash" only refuses overlaps with other bookings (staff may book any time).
    """
    end = start + timedelta(minutes=business.appointment_duration_minutes)
    busy = busy_intervals(db, business, start, end)
    if check == "clash":
        if any(b_start < as_utc(end) and as_utc(start) < b_end for b_start, b_end in busy):
            raise SlotUnavailable()
    else:
        if not is_slot_free(
            start,
            business.working_hours,
            business.timezone,
            business.appointment_duration_minutes,
            busy,
            datetime.now(timezone.utc),
            settings.MIN_BOOKING_NOTICE_MINUTES,
        ):
            raise SlotUnavailable()

    event_id = None
    calendar = _calendar(db, business)
    if calendar:
        event = calendar.create_event(
            build_event_body(client.id, client.name, client.phone_number, service_type, start, end, source)
        )
        event_id = event["id"]

    appointment = Appointment(
        business_id=business.id,
        client_id=client.id,
        google_event_id=event_id,
        start_time=as_utc(start),
        end_time=as_utc(end),
        service_type=service_type,
        status="confirmed",
        source=source,
    )
    db.add(appointment)
    client.conversation_status = "booked"
    if service_type:
        client.last_service_type = service_type
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(db: Session, business: Business, appointment: Appointment) -> None:
    if appointment.google_event_id:
        calendar = _calendar(db, business)
        if calendar:
            calendar.delete_event(appointment.google_event_id)
    appointment.status = "cancelled"
    db.commit()
