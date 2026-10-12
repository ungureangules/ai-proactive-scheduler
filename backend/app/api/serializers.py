from datetime import datetime, timezone

from app.models.models import Appointment, Client
from app.schemas.schemas import AppointmentOut, ClientOut
from app.services.availability import as_utc
from app.services.scheduler_logic import SchedulerService


def client_status(client: Client, next_appointment: datetime | None, next_outreach: datetime | None, now: datetime) -> str:
    if client.opted_out:
        return "opted_out"
    if client.ai_paused:
        return "paused"
    if next_appointment:
        return "booked"
    if client.conversation_status == "negotiating":
        return "negotiating"
    if next_outreach and next_outreach <= now:
        return "due"
    return "idle"


def client_out(client: Client, now: datetime | None = None) -> ClientOut:
    now = now or datetime.now(timezone.utc)
    confirmed = sorted((a for a in client.appointments if a.status == "confirmed"), key=lambda a: as_utc(a.start_time))
    past = [as_utc(a.start_time) for a in confirmed if as_utc(a.start_time) <= now]
    upcoming = [as_utc(a.start_time) for a in confirmed if as_utc(a.start_time) > now]
    next_appointment = upcoming[0] if upcoming else None
    next_outreach = None if next_appointment else SchedulerService.next_outreach_date(client)
    return ClientOut(
        id=client.id,
        name=client.name,
        phone_number=client.phone_number,
        email=client.email,
        notes=client.notes,
        avg_frequency_days=client.avg_frequency_days,
        frequency_confidence=client.frequency_confidence,
        last_service_type=client.last_service_type,
        last_visit=past[-1] if past else None,
        next_appointment=next_appointment,
        next_outreach=next_outreach,
        status=client_status(client, next_appointment, next_outreach, now),
        ai_paused=client.ai_paused,
        opted_out=client.opted_out,
    )


def appointment_out(appointment: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=appointment.id,
        client_id=appointment.client_id,
        client_name=appointment.client.name,
        start_time=as_utc(appointment.start_time),
        end_time=as_utc(appointment.end_time),
        service_type=appointment.service_type,
        status=appointment.status,
        source=appointment.source,
    )
