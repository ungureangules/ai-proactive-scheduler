from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


DEFAULT_WORKING_HOURS = {
    "monday": {"start": "09:00", "end": "18:00"},
    "tuesday": {"start": "09:00", "end": "18:00"},
    "wednesday": {"start": "09:00", "end": "18:00"},
    "thursday": {"start": "09:00", "end": "18:00"},
    "friday": {"start": "09:00", "end": "18:00"},
    "saturday": {"start": "09:00", "end": "13:00"},
    "sunday": None,
}


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="UTC")  # IANA name, e.g. "America/Sao_Paulo"
    working_hours = Column(JSON, nullable=False, default=lambda: dict(DEFAULT_WORKING_HOURS))  # day -> {"start","end"} or null when closed
    appointment_duration_minutes = Column(Integer, nullable=False, default=30)
    default_country_code = Column(String)  # digits only, e.g. "55"; used for phone numbers written without "+"
    outreach_enabled = Column(Boolean, nullable=False, default=True)

    # Encrypted JSON: token, refresh_token, scopes, expiry (see app.core.security)
    google_credentials_encrypted = Column(Text)
    google_account_email = Column(String)
    google_calendar_id = Column(String, nullable=False, default="primary")
    last_synced_at = Column(DateTime(timezone=True))
    last_outreach_run_on = Column(String)  # ISO date (business timezone) of the last outreach run
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    clients = relationship("Client", back_populates="business", cascade="all, delete-orphan")


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (UniqueConstraint("business_id", "phone_number", name="uq_client_business_phone"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, index=True)  # normalised E.164, e.g. "+5511999999999"
    email = Column(String)
    notes = Column(Text)

    avg_frequency_days = Column(Integer)  # average gap between past appointments
    frequency_confidence = Column(Float)  # 0..1, how regular those gaps are
    last_service_type = Column(String)

    conversation_status = Column(String, nullable=False, default="idle")  # "idle" | "negotiating" | "booked"
    ai_paused = Column(Boolean, nullable=False, default=False)  # staff took over the conversation
    opted_out = Column(Boolean, nullable=False, default=False)  # client asked not to be contacted
    last_outreach_at = Column(DateTime(timezone=True))
    staff_last_read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    business = relationship("Business", back_populates="clients")
    appointments = relationship("Appointment", back_populates="client", cascade="all, delete-orphan")
    messages = relationship("CommunicationLog", back_populates="client", cascade="all, delete-orphan")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("business_id", "google_event_id", name="uq_appointment_business_event"),)

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    google_event_id = Column(String)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    service_type = Column(String)
    status = Column(String, nullable=False, default="confirmed")  # "confirmed" | "cancelled"
    source = Column(String, nullable=False, default="google")  # "google" | "ai" | "manual"
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    client = relationship("Client", back_populates="appointments")


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    message_body = Column(Text, nullable=False)
    direction = Column(String, nullable=False)  # "inbound" | "outbound"
    sender = Column(String, nullable=False)  # "client" | "ai" | "staff" | "system"
    status = Column(String, nullable=False, default="sent")  # "received" | "sent" | "failed"
    error = Column(Text)
    provider_sid = Column(String, unique=True)  # Twilio MessageSid, used to drop duplicate webhooks
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    platform = Column(String, nullable=False, default="whatsapp")

    client = relationship("Client", back_populates="messages")
