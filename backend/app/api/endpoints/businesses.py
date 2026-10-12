import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Business
from app.schemas.schemas import BusinessOut, BusinessUpdate, GoogleStatus, IntegrationsOut, TwilioStatus
from app.services import google_calendar
from app.services.scheduler_logic import SchedulerService
from app.services.twilio_whatsapp import is_configured as twilio_configured

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/me", response_model=BusinessOut)
def get_business(business: Business = Depends(get_current_business)):
    return business


@router.patch("/me", response_model=BusinessOut)
def update_business(data: BusinessUpdate, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes:
        changes["email"] = changes["email"].lower()
        taken = db.query(Business).filter(Business.email == changes["email"], Business.id != business.id).first()
        if taken:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
    for field, value in changes.items():
        setattr(business, field, value)
    db.commit()
    return business


@router.get("/me/integrations", response_model=IntegrationsOut)
def get_integrations(business: Business = Depends(get_current_business)):
    return IntegrationsOut(
        google=GoogleStatus(
            connected=bool(business.google_credentials_encrypted),
            account_email=business.google_account_email,
            calendar_id=business.google_calendar_id if business.google_credentials_encrypted else None,
            last_synced_at=business.last_synced_at,
        ),
        twilio=TwilioStatus(
            configured=twilio_configured(),
            whatsapp_number=settings.TWILIO_WHATSAPP_NUMBER or None,
            outreach_template_configured=bool(settings.TWILIO_OUTREACH_CONTENT_SID),
        ),
    )


@router.get("/me/google/auth-url")
def get_google_auth_url(business: Business = Depends(get_current_business)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured on the server")
    return {"url": google_calendar.get_auth_url(business.id)}


@router.delete("/me/google", status_code=204)
def disconnect_google(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    google_calendar.disconnect_business(db, business)


@router.post("/me/sync")
def sync_calendar(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    if not business.google_credentials_encrypted:
        raise HTTPException(status_code=400, detail="Connect Google Calendar first")
    try:
        return SchedulerService.sync_and_analyze_frequency(db, business.id)
    except HttpError as exc:
        logger.exception("Calendar sync failed for business %s", business.id)
        raise HTTPException(status_code=502, detail="Google Calendar request failed") from exc


@router.get("/google-auth-callback")
def google_auth_callback(state: str, code: str | None = None, error: str | None = None, db: Session = Depends(get_db)):
    """Google redirects the browser here; the business is identified by the encrypted state only."""
    settings_url = f"{settings.FRONTEND_URL}/settings"
    parsed = google_calendar.parse_oauth_state(state)
    if not parsed or error or not code:
        return RedirectResponse(f"{settings_url}?google=error")
    business_id, verifier = parsed
    business = db.get(Business, business_id)
    if not business:
        return RedirectResponse(f"{settings_url}?google=error")
    try:
        google_calendar.connect_business(db, business, code, verifier)
    except Exception:
        logger.exception("Google OAuth exchange failed for business %s", business_id)
        db.rollback()
        return RedirectResponse(f"{settings_url}?google=error")
    return RedirectResponse(f"{settings_url}?google=connected")
