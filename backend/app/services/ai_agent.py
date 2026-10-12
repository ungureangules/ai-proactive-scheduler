import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Appointment, Business, Client, CommunicationLog
from app.services.availability import WEEKDAYS, as_utc
from app.services.booking import SlotUnavailable, available_slots, book_appointment, cancel_appointment

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6
HISTORY_LIMIT = 20
MAX_BOOKING_DAYS_AHEAD = 60

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "List free appointment start times on a date (business local time).",
            "parameters": {
                "type": "object",
                "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book the client into a free slot. Only call after the client has agreed to that exact date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM, 24h, business local time"},
                    "service_type": {"type": "string", "description": "e.g. Haircut"},
                },
                "required": ["date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_client_appointments",
            "description": "List this client's upcoming appointments.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel one of this client's upcoming appointments (e.g. before rebooking at another time).",
            "parameters": {
                "type": "object",
                "properties": {"appointment_id": {"type": "integer"}},
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hand_off_to_staff",
            "description": "Stop replying and ask a staff member to take over: complaints, questions you can't answer, prices, or anything not about scheduling.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
    },
]


def _describe_hours(working_hours: dict) -> str:
    parts = []
    for day in WEEKDAYS:
        hours = (working_hours or {}).get(day)
        parts.append(f"{day.title()}: {hours['start']}-{hours['end']}" if hours else f"{day.title()}: closed")
    return "; ".join(parts)


class AIAgentService:
    def __init__(self, db: Session, business: Business, client: Client):
        self.db = db
        self.business = business
        self.client = client
        self.tz = ZoneInfo(business.timezone)
        self.llm = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.handed_off = False

    def _system_prompt(self) -> str:
        now_local = datetime.now(self.tz)
        last_service = f" Their usual service is {self.client.last_service_type}." if self.client.last_service_type else ""
        frequency = (
            f" They usually come every {self.client.avg_frequency_days} days." if self.client.avg_frequency_days else ""
        )
        return (
            f"You are the WhatsApp scheduling assistant for {self.business.name}. "
            f"You are talking to {self.client.name}.{last_service}{frequency} "
            f"Now is {now_local:%A %Y-%m-%d %H:%M} ({self.business.timezone}). "
            f"Opening hours: {_describe_hours(self.business.working_hours)}. "
            f"Appointments last {self.business.appointment_duration_minutes} minutes.\n"
            "Rules:\n"
            "- Help the client book, move or cancel appointments. Be friendly and concise; this is WhatsApp.\n"
            "- Reply in the same language the client writes in.\n"
            "- Always call check_availability before offering times, and only offer times it returned.\n"
            "- Never say an appointment is booked or cancelled unless the tool call succeeded.\n"
            "- For anything other than scheduling, call hand_off_to_staff and tell the client someone will reply soon."
        )

    def _history(self) -> list[dict]:
        logs = (
            self.db.query(CommunicationLog)
            .filter(CommunicationLog.client_id == self.client.id, CommunicationLog.sender != "system")
            .order_by(CommunicationLog.timestamp.desc(), CommunicationLog.id.desc())
            .limit(HISTORY_LIMIT)
            .all()
        )
        messages = []
        for log in reversed(logs):
            if log.direction == "inbound":
                messages.append({"role": "user", "content": log.message_body})
            else:
                prefix = "[Sent by staff] " if log.sender == "staff" else ""
                messages.append({"role": "assistant", "content": prefix + log.message_body})
        return messages

    def _parse_date(self, value: str) -> date:
        day = date.fromisoformat(value)
        today = datetime.now(self.tz).date()
        if day < today or day > today + timedelta(days=MAX_BOOKING_DAYS_AHEAD):
            raise ValueError(f"date must be between {today} and {today + timedelta(days=MAX_BOOKING_DAYS_AHEAD)}")
        return day

    def _run_tool(self, name: str, args: dict) -> dict:
        try:
            if name == "check_availability":
                day = self._parse_date(args["date"])
                slots = available_slots(self.db, self.business, day)
                return {"date": day.isoformat(), "weekday": WEEKDAYS[day.weekday()], "free_times": [s.strftime("%H:%M") for s in slots]}

            if name == "book_appointment":
                day = self._parse_date(args["date"])
                start = datetime.combine(day, time.fromisoformat(args["time"]), tzinfo=self.tz)
                service = args.get("service_type") or self.client.last_service_type
                try:
                    appointment = book_appointment(self.db, self.business, self.client, start, service, source="ai")
                except SlotUnavailable:
                    return {"ok": False, "error": "That time is not available. Check availability again."}
                return {"ok": True, "appointment_id": appointment.id, "start": start.strftime("%A %Y-%m-%d %H:%M"), "service": service}

            if name == "list_client_appointments":
                return {"appointments": [self._describe(a) for a in self._upcoming()]}

            if name == "cancel_appointment":
                appointment = next((a for a in self._upcoming() if a.id == args["appointment_id"]), None)
                if not appointment:
                    return {"ok": False, "error": "No such upcoming appointment for this client."}
                cancel_appointment(self.db, self.business, appointment)
                return {"ok": True}

            if name == "hand_off_to_staff":
                self.client.ai_paused = True
                self.db.add(
                    CommunicationLog(
                        business_id=self.business.id,
                        client_id=self.client.id,
                        message_body=f"AI handed this conversation to staff: {args.get('reason', '')}",
                        direction="outbound",
                        sender="system",
                        status="sent",
                    )
                )
                self.db.commit()
                self.handed_off = True
                return {"ok": True}
        except (KeyError, ValueError) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": False, "error": f"Unknown tool {name}"}

    def _upcoming(self) -> list[Appointment]:
        now = datetime.now(timezone.utc)
        return [
            a
            for a in sorted(self.client.appointments, key=lambda a: as_utc(a.start_time))
            if a.status == "confirmed" and as_utc(a.start_time) > now
        ]

    def _describe(self, appointment: Appointment) -> dict:
        local = as_utc(appointment.start_time).astimezone(self.tz)
        return {"appointment_id": appointment.id, "start": local.strftime("%A %Y-%m-%d %H:%M"), "service": appointment.service_type}

    def reply(self) -> str:
        """Generate the next reply from the stored conversation (the latest inbound message included)."""
        messages = [{"role": "system", "content": self._system_prompt()}, *self._history()]
        for _ in range(MAX_TOOL_ROUNDS):
            response = self.llm.chat.completions.create(model=settings.OPENAI_MODEL, messages=messages, tools=TOOLS, timeout=60)
            message = response.choices[0].message
            if not message.tool_calls:
                return (message.content or "").strip()
            messages.append(message.model_dump(exclude_none=True))
            for call in message.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = self._run_tool(call.function.name, args)
                logger.info("AI tool %s(%s) -> %s", call.function.name, args, result)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        raise RuntimeError("AI agent exceeded tool-call limit")
