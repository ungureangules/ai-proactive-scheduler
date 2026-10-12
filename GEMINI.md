# GEMINI.md - AI Proactive Scheduling System

## Project Overview
This project is an AI-powered proactive scheduling system designed for businesses with recurring clients (e.g., barbershops, salons, medical clinics). It automatically analyzes historical appointment data from Google Calendar to determine client service frequencies and uses a conversational AI agent (LangChain + OpenAI) to proactively contact clients via WhatsApp (Twilio) to suggest and negotiate upcoming appointments.

### Architecture
*   **Backend**: Python FastAPI application managing the API, database (PostgreSQL), and AI orchestration.
*   **Worker**: Celery background tasks for syncing calendar data, analyzing frequencies, and performing automated outreach.
*   **Frontend**: Next.js (App Router) dashboard for business owners to monitor AI activity, manage settings, and view performance metrics.
*   **Infrastructure**: Fully containerized using Docker and Docker Compose.

### Tech Stack
*   **Language**: Python 3.11, TypeScript
*   **Frameworks**: FastAPI (Backend), Next.js (Frontend), Celery (Tasks)
*   **AI**: LangChain, OpenAI GPT-4o-mini
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
    # Edit backend/.env with your credentials
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
*   **Backend**: Run tests using `pytest` (TODO: Add unit tests).
*   **Frontend**: Run `npm run lint` and `npm run build` to verify integrity.

---

## Development Conventions

### Backend (FastAPI)
*   **Modular Routing**: All endpoints are organized under `app/api/endpoints` and aggregated in `app/api/api.py`.
*   **Service Layer**: Business logic, AI orchestration, and third-party integrations (Google, Twilio) reside in `app/services`.
*   **Data Models**: Use SQLAlchemy models in `app/models` and Pydantic schemas for request/response validation.
*   **Background Tasks**: All long-running or scheduled processes must be implemented as Celery tasks in `app/tasks`.

### Frontend (Next.js)
*   **App Router**: Use the Next.js App Router for all new pages.
*   **Components**: Reusable UI components should be placed in `src/components`.
*   **Styling**: Use Tailwind CSS for all styling.
*   **Icons**: Use `lucide-react` for a consistent iconography.

### API Standards
*   RESTful principles for the main API.
*   JSON response format.
*   Versioned endpoints (prefix: `/api/v1`).
