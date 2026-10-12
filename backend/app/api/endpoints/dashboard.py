from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_business
from app.api.serializers import appointment_out
from app.db.session import get_db
from app.models.models import Appointment, Business, Client, CommunicationLog
from app.schemas.schemas import DashboardOut

router = APIRouter()


@router.get("/", response_model=DashboardOut)
def get_dashboard(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    confirmed = db.query(Appointment).filter(Appointment.business_id == business.id, Appointment.status == "confirmed")

    upcoming_query = confirmed.filter(Appointment.start_time >= now)
    ai_bookings = (
        db.query(func.count(Appointment.id))
        .filter(Appointment.business_id == business.id, Appointment.source == "ai", Appointment.created_at >= month_ago)
        .scalar()
    )
    # Clients contacted proactively in the last 30 days, and how many of those booked through the AI
    contacted = (
        db.query(Client.id)
        .filter(Client.business_id == business.id, Client.last_outreach_at >= month_ago)
        .subquery()
    )
    contacted_count = db.query(func.count()).select_from(contacted).scalar()
    converted = (
        db.query(func.count(func.distinct(Appointment.client_id)))
        .filter(
            Appointment.business_id == business.id,
            Appointment.source == "ai",
            Appointment.created_at >= month_ago,
            Appointment.client_id.in_(db.query(contacted.c.id)),
        )
        .scalar()
    )
    outreach_sent = (
        db.query(func.count(CommunicationLog.id))
        .filter(
            CommunicationLog.business_id == business.id,
            CommunicationLog.direction == "outbound",
            CommunicationLog.sender == "ai",
            CommunicationLog.status == "sent",
            CommunicationLog.timestamp >= month_ago,
        )
        .scalar()
    )
    active_clients = (
        db.query(func.count(func.distinct(Appointment.client_id)))
        .filter(Appointment.business_id == business.id, Appointment.status == "confirmed", Appointment.start_time >= now - timedelta(days=180))
        .scalar()
    )
    upcoming = upcoming_query.options(joinedload(Appointment.client)).order_by(Appointment.start_time).limit(8).all()
    return DashboardOut(
        upcoming_appointments=upcoming_query.count(),
        ai_bookings_30d=ai_bookings,
        outreach_sent_30d=outreach_sent,
        conversion_rate_30d=round(converted / contacted_count, 3) if contacted_count else None,
        active_clients=active_clients,
        upcoming=[appointment_out(a) for a in upcoming],
    )
