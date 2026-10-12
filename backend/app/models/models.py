from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Interval, Float, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    timezone = Column(String, default="UTC")
    working_hours = Column(JSON) # e.g., {"monday": {"start": "09:00", "end": "18:00"}, ...}
    google_oauth_token = Column(JSON) # Stores access_token, refresh_token, etc.
    
    clients = relationship("Client", back_populates="business")

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    name = Column(String)
    phone_number = Column(String, index=True)
    avg_frequency_days = Column(Integer) # Calculated average gap between appointments
    
    business = relationship("Business", back_populates="clients")
    appointments = relationship("Appointment", back_populates="client")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    google_event_id = Column(String, unique=True, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    service_type = Column(String)
    status = Column(String) # e.g., "confirmed", "proposed", "cancelled"
    
    client = relationship("Client", back_populates="appointments")

class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    message_body = Column(String)
    direction = Column(String) # "inbound" or "outbound"
    timestamp = Column(DateTime, default=datetime.utcnow)
    platform = Column(String, default="whatsapp")
