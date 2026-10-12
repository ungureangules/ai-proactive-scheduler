from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import Business
from app.services.google_calendar import GoogleCalendarService

router = APIRouter()

@router.get("/")
async def get_businesses(db: Session = Depends(get_db)):
    return db.query(Business).all()

@router.get("/google-auth-url")
async def get_google_auth_url():
    url, state = GoogleCalendarService.get_auth_url()
    return {"url": url}

@router.get("/google-auth-callback")
async def google_auth_callback(code: str, business_id: int, db: Session = Depends(get_db)):
    credentials = GoogleCalendarService.get_credentials_from_code(code)
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business.google_oauth_token = credentials
    db.commit()
    return {"message": "Google Calendar connected successfully"}
