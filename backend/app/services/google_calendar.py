import secrets
from datetime import datetime, timezone

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_json, encrypt_json
from app.models.models import Business

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_URI = "https://oauth2.googleapis.com/token"
OAUTH_STATE_MAX_AGE_SECONDS = 600


class GoogleNotConnected(Exception):
    pass


def _flow(**kwargs) -> Flow:
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": TOKEN_URI,
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        **kwargs,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def get_auth_url(business_id: int) -> str:
    # The callback runs in a separate request, so the PKCE verifier travels inside the
    # encrypted (and therefore unreadable, unforgeable, expiring) OAuth state value.
    verifier = secrets.token_urlsafe(64)
    state = encrypt_json({"business_id": business_id, "verifier": verifier, "purpose": "google_oauth"})
    flow = _flow(code_verifier=verifier, autogenerate_code_verifier=False)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",  # always return a refresh token, even on reconnect
        state=state,
    )
    return url


def parse_oauth_state(state: str) -> tuple[int, str] | None:
    data = decrypt_json(state, max_age_seconds=OAUTH_STATE_MAX_AGE_SECONDS)
    if not data or data.get("purpose") != "google_oauth":
        return None
    return int(data["business_id"]), data["verifier"]


def connect_business(db: Session, business: Business, code: str, verifier: str) -> None:
    flow = _flow(code_verifier=verifier, autogenerate_code_verifier=False)
    flow.fetch_token(code=code)
    _store_credentials(business, flow.credentials)
    calendar = GoogleCalendarClient(db, business)
    business.google_account_email = calendar.primary_calendar_id()
    business.google_calendar_id = "primary"
    db.commit()


def disconnect_business(db: Session, business: Business) -> None:
    data = decrypt_json(business.google_credentials_encrypted) if business.google_credentials_encrypted else None
    if data:
        token = data.get("refresh_token") or data.get("token")
        try:
            httpx.post("https://oauth2.googleapis.com/revoke", data={"token": token}, timeout=10)
        except httpx.HTTPError:
            pass  # the token is dropped locally either way
    business.google_credentials_encrypted = None
    business.google_account_email = None
    business.last_synced_at = None
    db.commit()


def _store_credentials(business: Business, credentials: Credentials) -> None:
    business.google_credentials_encrypted = encrypt_json(
        {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "scopes": list(credentials.scopes or SCOPES),
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }
    )


class GoogleCalendarClient:
    """Calendar API client for one business. Refreshed tokens are saved back to the business."""

    def __init__(self, db: Session, business: Business):
        data = decrypt_json(business.google_credentials_encrypted) if business.google_credentials_encrypted else None
        if not data:
            raise GoogleNotConnected()
        self.db = db
        self.business = business
        expiry = datetime.fromisoformat(data["expiry"]) if data.get("expiry") else None
        self.credentials = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri=TOKEN_URI,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=data.get("scopes") or SCOPES,
            # google-auth compares expiry against a naive UTC datetime
            expiry=expiry.astimezone(timezone.utc).replace(tzinfo=None) if expiry else None,
        )
        if not self.credentials.valid:
            self.credentials.refresh(Request())
            _store_credentials(business, self.credentials)
            db.flush()
        self.service = build("calendar", "v3", credentials=self.credentials, cache_discovery=False)
        self.calendar_id = business.google_calendar_id or "primary"

    def primary_calendar_id(self) -> str:
        return self.service.calendars().get(calendarId="primary").execute()["id"]

    def list_events(self, time_min: datetime, time_max: datetime) -> list[dict]:
        events, page_token = [], None
        while True:
            result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=time_min.isoformat(),
                    timeMax=time_max.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=2500,
                    pageToken=page_token,
                )
                .execute()
            )
            events.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                return events

    def busy_intervals(self, time_min: datetime, time_max: datetime) -> list[tuple[datetime, datetime]]:
        result = (
            self.service.freebusy()
            .query(body={"timeMin": time_min.isoformat(), "timeMax": time_max.isoformat(), "items": [{"id": self.calendar_id}]})
            .execute()
        )
        busy = result.get("calendars", {}).get(self.calendar_id, {}).get("busy", [])
        return [(datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"])) for b in busy]

    def create_event(self, event_data: dict) -> dict:
        return self.service.events().insert(calendarId=self.calendar_id, body=event_data).execute()

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()


def build_event_body(client_id: int, client_name: str, phone: str | None, service: str | None, start: datetime, end: datetime, booked_by: str) -> dict:
    title = f"{service} ({client_name})" if service else client_name
    description = f"Phone: {phone}\nBooked by: {booked_by}" if phone else f"Booked by: {booked_by}"
    return {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "extendedProperties": {"private": {"client_id": str(client_id), "service_type": service or "", "source": booked_by}},
    }
