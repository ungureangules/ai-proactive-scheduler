from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session, joinedload
from zoneinfo import ZoneInfo

from app.api.deps import get_current_business
from app.api.endpoints.clients import get_client_or_404
from app.api.serializers import appointment_out
from app.db.session import get_db
from app.models.models import Appointment, Business
from app.schemas.schemas import AppointmentIn, AppointmentOut
from app.services.availability import as_utc
from app.services.booking import SlotUnavailable, book_appointment, cancel_appointment

router = APIRouter()


@router.get("/", response_model=list[AppointmentOut])
def list_appointments(
    start: datetime = Query(description="ISO datetime with timezone"),
    end: datetime = Query(description="ISO datetime with timezone"),
    include_cancelled: bool = False,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    start, end = as_utc(start), as_utc(end)
    query = (
        db.query(Appointment)
        .options(joinedload(Appointment.client))
        .filter(Appointment.business_id == business.id, Appointment.start_time >= start, Appointment.start_time < end)
    )
    if not include_cancelled:
        query = query.filter(Appointment.status == "confirmed")
    return [appointment_out(a) for a in query.order_by(Appointment.start_time).all()]


@router.post("/", response_model=AppointmentOut, status_code=201)
def create_appointment(data: AppointmentIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    client = get_client_or_404(db, business, data.client_id)
    start = datetime.combine(data.date, data.time, tzinfo=ZoneInfo(business.timezone))
    try:
        # Staff may book outside opening hours; only clashes with other bookings are refused.
        appointment = book_appointment(db, business, client, start, data.service_type, source="manual", check="clash")
    except SlotUnavailable:
        raise HTTPException(status_code=409, detail="That time overlaps another booking")
    except HttpError as exc:
        raise HTTPException(status_code=502, detail="Could not create the Google Calendar event") from exc
    return appointment_out(appointment)


@router.delete("/{appointment_id}", status_code=204)
def delete_appointment(appointment_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    appointment = db.get(Appointment, appointment_id)
    if not appointment or appointment.business_id != business.id:
        raise HTTPException(status_code=404, detail="Appointment not found")
    try:
        cancel_appointment(db, business, appointment)
    except HttpError as exc:
        raise HTTPException(status_code=502, detail="Could not delete the Google Calendar event") from exc
