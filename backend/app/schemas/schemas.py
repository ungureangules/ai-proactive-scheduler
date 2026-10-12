from datetime import date, datetime, time
from typing import Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES
from app.services.availability import WEEKDAYS


def _check_timezone(value: str) -> str:
    if value not in available_timezones():
        raise ValueError("unknown timezone")
    return value


def _check_working_hours(value: dict) -> dict:
    cleaned = {}
    for day in WEEKDAYS:
        hours = value.get(day)
        if not hours:
            cleaned[day] = None
            continue
        start, end = time.fromisoformat(hours["start"]), time.fromisoformat(hours["end"])
        if end <= start:
            raise ValueError(f"{day}: end must be after start")
        cleaned[day] = {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")}
    return cleaned


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterIn(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8)
    timezone: str = "UTC"

    @field_validator("timezone")
    @classmethod
    def tz(cls, value: str) -> str:
        return _check_timezone(value)

    @field_validator("password")
    @classmethod
    def password_length(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    timezone: str
    working_hours: dict
    appointment_duration_minutes: int
    default_country_code: str | None
    outreach_enabled: bool


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    timezone: str | None = None
    working_hours: dict | None = None
    appointment_duration_minutes: int | None = Field(default=None, ge=5, le=480)
    default_country_code: str | None = Field(default=None, pattern=r"^\d{1,4}$")
    outreach_enabled: bool | None = None

    @field_validator("timezone")
    @classmethod
    def tz(cls, value):
        return value if value is None else _check_timezone(value)

    @field_validator("working_hours")
    @classmethod
    def hours(cls, value):
        return value if value is None else _check_working_hours(value)


class GoogleStatus(BaseModel):
    connected: bool
    account_email: str | None
    calendar_id: str | None
    last_synced_at: datetime | None


class TwilioStatus(BaseModel):
    configured: bool
    whatsapp_number: str | None
    outreach_template_configured: bool


class IntegrationsOut(BaseModel):
    google: GoogleStatus
    twilio: TwilioStatus


class ClientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone_number: str
    email: EmailStr | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone_number: str | None = None
    email: EmailStr | None = None
    notes: str | None = None
    ai_paused: bool | None = None
    opted_out: bool | None = None


class ClientOut(BaseModel):
    id: int
    name: str
    phone_number: str | None
    email: str | None
    notes: str | None
    avg_frequency_days: int | None
    frequency_confidence: float | None
    last_service_type: str | None
    last_visit: datetime | None
    next_appointment: datetime | None
    next_outreach: datetime | None
    status: Literal["idle", "due", "negotiating", "booked", "paused", "opted_out"]
    ai_paused: bool
    opted_out: bool


class AppointmentIn(BaseModel):
    client_id: int
    date: date
    time: time  # business local time
    service_type: str | None = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    client_name: str
    start_time: datetime
    end_time: datetime
    service_type: str | None
    status: str
    source: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_body: str
    direction: str
    sender: str
    status: str
    error: str | None
    timestamp: datetime


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=1600)


class ConversationOut(BaseModel):
    client_id: int
    client_name: str
    phone_number: str | None
    last_message: str
    last_message_at: datetime
    unread: bool
    status: str
    ai_paused: bool


class DashboardOut(BaseModel):
    upcoming_appointments: int
    ai_bookings_30d: int
    outreach_sent_30d: int
    conversion_rate_30d: float | None
    active_clients: int
    upcoming: list[AppointmentOut]
