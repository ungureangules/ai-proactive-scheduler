"""Turning Google Calendar events into client visits.

Convention for events created by hand in Google Calendar:
  * title: "Service (Client Name)" or "Service - Client Name"; any other title is
    treated as the client name with no service
  * description: contains the client's phone number, e.g. "Phone: +55 11 99999-9999"
Events created by this app carry the client id in extendedProperties.private.client_id.
"""
import re
import statistics
from dataclasses import dataclass
from datetime import datetime

# Either an international number ("+55 11 ...") anywhere, or any number after a label,
# so dates and prices in the description aren't mistaken for phone numbers.
PHONE_RE = re.compile(
    r"(\+\d[\d\s().-]{6,}\d)"
    r"|(?:phone|tel|telefone|whatsapp|celular|cel|mobile)\s*[:.]?\s*(\(?\d[\d\s().-]{6,}\d)",
    re.IGNORECASE,
)
TITLE_PARENS_RE = re.compile(r"^\s*(?P<service>.+?)\s*\((?P<name>[^()]+)\)\s*$")
TITLE_DASH_RE = re.compile(r"^\s*(?P<service>.+?)\s+[-–—]\s+(?P<name>.+?)\s*$")


@dataclass
class ParsedEvent:
    event_id: str
    start: datetime
    end: datetime
    client_name: str
    service_type: str | None
    phone_number: str | None
    client_id: int | None


def normalize_phone(raw: str | None, default_country_code: str | None = None) -> str | None:
    """Return an E.164 number ("+5511999999999") or None if `raw` doesn't look like one."""
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("whatsapp:"):
        raw = raw[len("whatsapp:"):]
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        pass
    elif digits.startswith("00"):
        digits = digits[2:]
    elif default_country_code:
        digits = default_country_code.lstrip("+") + digits.lstrip("0")
    else:
        return None
    if not 8 <= len(digits) <= 15:
        return None
    return f"+{digits}"


def parse_title(summary: str) -> tuple[str, str | None]:
    """Return (client_name, service_type) from an event title."""
    summary = (summary or "").strip()
    for pattern in (TITLE_PARENS_RE, TITLE_DASH_RE):
        match = pattern.match(summary)
        if match:
            return match["name"].strip(), match["service"].strip()
    return summary, None


def parse_event(event: dict, default_country_code: str | None = None) -> ParsedEvent | None:
    """Parse a Google Calendar event; returns None for events that can't be appointments."""
    if event.get("status") == "cancelled":
        return None
    start_raw = event.get("start", {}).get("dateTime")
    end_raw = event.get("end", {}).get("dateTime")
    if not start_raw or not end_raw:
        return None  # all-day events (holidays, days off) aren't appointments
    start = datetime.fromisoformat(start_raw)
    end = datetime.fromisoformat(end_raw)

    name, service = parse_title(event.get("summary", ""))
    phone = None
    match = PHONE_RE.search(event.get("description") or "")
    if match:
        phone = normalize_phone(match.group(1) or match.group(2), default_country_code)

    client_id = None
    private = event.get("extendedProperties", {}).get("private", {})
    if private.get("client_id", "").isdigit():
        client_id = int(private["client_id"])
        service = private.get("service_type") or service

    if not name and client_id is None:
        return None
    return ParsedEvent(
        event_id=event["id"],
        start=start,
        end=end,
        client_name=name,
        service_type=service,
        phone_number=phone,
        client_id=client_id,
    )


def analyze_frequency(visits: list[datetime]) -> tuple[int, float] | None:
    """Average gap in days between visits and a 0..1 confidence score, or None if not enough data."""
    days = sorted({v.date() for v in visits})  # several events on one day count as one visit
    if len(days) < 2:
        return None
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    avg = statistics.mean(gaps)
    spread = statistics.pstdev(gaps) / avg if avg else 1.0
    regularity = max(0.0, 1.0 - min(spread, 1.0))
    sample = min(1.0, len(gaps) / 4)  # four or more gaps = full weight
    return round(avg), round(regularity * sample, 2)
