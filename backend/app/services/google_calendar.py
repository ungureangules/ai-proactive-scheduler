from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.core.config import settings
from datetime import datetime
import json

SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarService:
    @staticmethod
    def get_auth_url():
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return authorization_url, state

    @staticmethod
    def get_credentials_from_code(code):
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }

    @staticmethod
    def get_calendar_client(token_dict):
        credentials = Credentials.from_authorized_user_info(token_dict, SCOPES)
        return build('calendar', 'v3', credentials=credentials)

    @staticmethod
    def get_upcoming_events(token_dict, calendar_id='primary', max_results=10):
        service = GoogleCalendarService.get_calendar_client(token_dict)
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])

    @staticmethod
    def create_event(token_dict, event_data, calendar_id='primary'):
        service = GoogleCalendarService.get_calendar_client(token_dict)
        event = service.events().insert(calendarId=calendar_id, body=event_data).execute()
        return event

    @staticmethod
    def update_event(token_dict, event_id, event_data, calendar_id='primary'):
        service = GoogleCalendarService.get_calendar_client(token_dict)
        event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event_data).execute()
        return event

    @staticmethod
    def delete_event(token_dict, event_id, calendar_id='primary'):
        service = GoogleCalendarService.get_calendar_client(token_dict)
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
