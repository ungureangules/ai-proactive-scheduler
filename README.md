# FullCalendar

FullCalendar is an AI-powered proactive scheduling system designed for businesses with recurring clients (e.g., barbershops, salons, medical clinics). It automatically analyzes historical appointment data from Google Calendar to determine client service frequencies and uses a conversational AI agent to proactively contact clients via WhatsApp to suggest and negotiate upcoming appointments.

## Key Features
- **AI Outreach**: Proactive WhatsApp messaging using LangChain and OpenAI.
- **Calendar Sync**: Seamless integration with Google Calendar API.
- **Business Dashboard**: Next.js-based frontend for monitoring and settings.
- **Automated Scheduling**: Smart logic to predict when clients need their next service.

## Tech Stack
- **Backend**: FastAPI, PostgreSQL, SQLAlchemy, Celery, Redis.
- **Frontend**: Next.js (App Router), Tailwind CSS, Lucide React.
- **AI/ML**: LangChain, OpenAI GPT-4o-mini.
- **Communication**: Twilio (WhatsApp Business API).

## Getting Started

### Prerequisites
- Docker & Docker Compose
- API Keys: OpenAI, Twilio, Google Cloud Project (Calendar API).

### Setup
1. Clone the repository.
2. Create a `.env` file in the `backend/` directory based on `backend/.env.example`.
3. Run the application:
   ```bash
   docker-compose up --build
   ```

## License
Private / Proprietary
