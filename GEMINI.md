# GEMINI.md - AI Proactive Scheduling System

## Project Overview
This project is an AI-powered proactive scheduling system designed for businesses with recurring clients (e.g., barbershops, salons, medical clinics). It automatically analyzes historical appointment data from Google Calendar to determine client service frequencies and uses a conversational AI agent (OpenAI tool calling) to proactively contact clients via WhatsApp (Twilio) to suggest and negotiate upcoming appointments.

### Architecture
*   **Backend**: Python FastAPI application managing the API, database (PostgreSQL), and AI orchestration.
*   **Worker**: Celery background tasks for syncing calendar data, analyzing frequencies, performing automated outreach, and generating AI replies to inbound WhatsApp messages.
*   **Beat**: Celery beat runs `run_outreach_cycle` hourly; each business is synced every hour and contacted at `OUTREACH_LOCAL_HOUR` in its own timezone.
*   **Frontend**: Next.js (App Router) dashboard for business owners to monitor AI activity, manage settings, and view performance metrics.
*   **Infrastructure**: Fully containerized using Docker and Docker Compose.

### Tech Stack
*   **Language**: Python 3.11, TypeScript
*   **Frameworks**: FastAPI (Backend), Next.js (Frontend), Celery (Tasks)
*   **AI**: OpenAI SDK (chat completions + tool calling), GPT-4o-mini by default (`OPENAI_MODEL`)
*   **Database**: PostgreSQL (SQLAlchemy ORM)
*   **Integrations**: Google Calendar API (OAuth2), Twilio Messaging API (WhatsApp)
*   **Cache/Broker**: Redis

---

## Building and Running

### Prerequisites
*   Docker & Docker Compose
*   API keys for OpenAI, Twilio, and a Google Cloud Project with Calendar API enabled.

### Local Development
1.  **Configure Environment**:
    ```bash
    cp backend/.env.example backend/.env
    # Edit backend/.env with your credentials; SECRET_KEY and ENCRYPTION_KEY are required
    ```
2.  **Start the Stack**:
    ```bash
    docker-compose up --build
    ```
3.  **Access Points**:
    *   **Frontend**: http://localhost:3000
    *   **Backend API**: http://localhost:8000
    *   **API Docs**: http://localhost:8000/docs

### Testing
*   **Backend**: `pip install -r requirements-dev.txt && pytest` (from `backend/`). Tests use SQLite and mock Google, Twilio and OpenAI.
*   **Frontend**: Run `npm run lint` and `npm run build` to verify integrity.

---

## Development Conventions

### Backend (FastAPI)
*   **Modular Routing**: All endpoints are organized under `app/api/endpoints` and aggregated in `app/api/api.py`.
*   **Service Layer**: Business logic, AI orchestration, and third-party integrations (Google, Twilio) reside in `app/services`.
*   **Data Models**: Use SQLAlchemy models in `app/models` and Pydantic schemas for request/response validation.
*   **Background Tasks**: All long-running or scheduled processes must be implemented as Celery tasks in `app/tasks`.
*   **Migrations**: Schema changes go through Alembic: `alembic revision --autogenerate -m "..."`, then `alembic upgrade head` (the backend container runs it on start).
*   **Auth**: Every endpoint except `/auth/register`, `/auth/login`, the Google OAuth callback and the Twilio webhook requires a bearer token; always scope queries to the current business.
*   **Datetimes**: Store timezone-aware UTC (`DateTime(timezone=True)`); convert to the business's IANA timezone only for display and for opening hours.

### Domain Conventions
*   **Clients from Google Calendar**: events are linked to clients by `extendedProperties.private.client_id` (events the app creates), then by a phone number in the description (`Phone: +55 11 99999-9999`), then by an exact, unique client name. Titles like `Haircut (Bob Silva)` or `Haircut - Bob Silva` give the service and name. All-day events are ignored.
*   **WhatsApp**: proactive outreach must use an approved template (`TWILIO_OUTREACH_CONTENT_SID`); free-form messages only deliver within 24h of the client's last message. Replies of STOP/PARAR opt a client out.
*   **AI safety**: the agent may only offer times returned by `check_availability` and may only claim a booking after `book_appointment` succeeds. Staff replies and failures pause the AI for that client.

### Frontend (Next.js)
*   **App Router**: Use the Next.js App Router for all new pages.
*   **Components**: Reusable UI components should be placed in `src/components`.
*   **Styling**: Use Tailwind CSS for all styling.
*   **Icons**: Use `lucide-react` for a consistent iconography.

### API Standards
*   RESTful principles for the main API.
*   JSON response format.
*   Versioned endpoints (prefix: `/api/v1`).
