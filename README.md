# FullCalendar

FullCalendar is an AI-powered proactive scheduling system designed for businesses with recurring clients (e.g., barbershops, salons, medical clinics). It automatically analyzes historical appointment data from Google Calendar to determine client service frequencies and uses a conversational AI agent to proactively contact clients via WhatsApp to suggest and negotiate upcoming appointments.

## Key Features
- **AI Outreach**: Proactive WhatsApp messaging, with an OpenAI agent that checks availability and books appointments.
- **Calendar Sync**: Seamless integration with Google Calendar API.
- **Business Dashboard**: Next.js-based frontend for monitoring and settings.
- **Automated Scheduling**: Smart logic to predict when clients need their next service.

## Tech Stack
- **Backend**: FastAPI, PostgreSQL, SQLAlchemy, Celery, Redis.
- **Frontend**: Next.js (App Router), Tailwind CSS, Lucide React.
- **AI/ML**: OpenAI GPT-4o-mini (tool calling).
- **Communication**: Twilio (WhatsApp Business API).

## Getting Started

### Prerequisites
- Docker & Docker Compose
- API Keys: OpenAI, Twilio, Google Cloud Project (Calendar API).

### Setup
1. Clone the repository.
2. Create a `.env` file in the `backend/` directory based on `backend/.env.example`. `SECRET_KEY` and `ENCRYPTION_KEY` are required; the file shows how to generate them.
3. Run the application:
   ```bash
   docker-compose up --build
   ```
4. Open http://localhost:3000, create an account, then connect Google Calendar in Settings.
5. Point your Twilio WhatsApp webhook at `<PUBLIC_BASE_URL>/api/v1/webhooks/whatsapp` (use a tunnel such as ngrok locally, and set `PUBLIC_BASE_URL` to it so signatures validate).

### Calendar events
The AI learns each client's visit frequency from your Google Calendar. To link an event to a client, put their phone number in the event description (e.g. `Phone: +55 11 99999-9999`) or add the client on the Clients page with the same name used in event titles like `Haircut (Bob Silva)`.

### Tests
```bash
cd backend && pip install -r requirements-dev.txt && pytest
```

## License
Private / Proprietary
