from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/scheduler"

    # Required: there are no safe defaults for these. See .env.example for how to generate them.
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # Public URLs, used for CORS, OAuth redirects and Twilio signature validation
    FRONTEND_URL: str = "http://localhost:3000"
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""
    # WhatsApp only allows business-initiated messages through an approved template.
    # Variables: {{1}} client name, {{2}} business name, {{3}} days since last visit.
    TWILIO_OUTREACH_CONTENT_SID: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/businesses/google-auth-callback"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Scheduling behaviour
    SYNC_LOOKBACK_DAYS: int = 365
    SYNC_LOOKAHEAD_DAYS: int = 90
    OUTREACH_LOCAL_HOUR: int = 10  # hour of day (business timezone) when outreach runs
    OUTREACH_LEAD_DAYS: int = 2  # contact clients this many days before they're due
    OUTREACH_COOLDOWN_DAYS: int = 14  # minimum gap between proactive messages to one client
    MIN_BOOKING_NOTICE_MINUTES: int = 60

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_is_real(cls, value: str) -> str:
        if len(value) < 32 or value.startswith("generate_a_secure"):
            raise ValueError("SECRET_KEY must be a random string of at least 32 characters (see .env.example)")
        return value


settings = Settings()
