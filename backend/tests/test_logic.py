from datetime import date, datetime, timedelta, timezone

from app.core.security import create_access_token, decode_access_token, decrypt_json, encrypt_json, hash_password, verify_password
from app.models.models import DEFAULT_WORKING_HOURS
from app.services.availability import free_slots, is_slot_free
from app.services.event_parsing import analyze_frequency, normalize_phone, parse_event, parse_title
from app.services.google_calendar import parse_oauth_state
from zoneinfo import ZoneInfo

SP = "America/Sao_Paulo"


def test_normalize_phone():
    assert normalize_phone("+55 (11) 99999-9999") == "+5511999999999"
    assert normalize_phone("whatsapp:+14155550100") == "+14155550100"
    assert normalize_phone("0044 20 7946 0958") == "+442079460958"
    assert normalize_phone("(11) 99999-9999", "55") == "+5511999999999"
    assert normalize_phone("011 99999-9999", "55") == "+5511999999999"
    assert normalize_phone("99999-9999") is None  # no country code known
    assert normalize_phone("+12") is None


def test_parse_title():
    assert parse_title("Haircut (Bob S.)") == ("Bob S.", "Haircut")
    assert parse_title("Beard Trim - Ray J.") == ("Ray J.", "Beard Trim")
    assert parse_title("Ana Paula") == ("Ana Paula", None)


def test_parse_event_handles_offsets_and_skips_all_day():
    event = {
        "id": "e1",
        "summary": "Haircut (Bob)",
        "description": "Phone: +55 11 98888-7777\nPaid R$ 50,00 on 2026-10-01",
        "start": {"dateTime": "2026-10-01T09:00:00-03:00"},
        "end": {"dateTime": "2026-10-01T09:30:00-03:00"},
    }
    parsed = parse_event(event)
    assert parsed.client_name == "Bob" and parsed.service_type == "Haircut"
    assert parsed.phone_number == "+5511988887777"
    assert parsed.start.utcoffset() == timedelta(hours=-3)
    assert parse_event({"id": "e2", "summary": "Holiday", "start": {"date": "2026-10-12"}, "end": {"date": "2026-10-13"}}) is None
    # dates and prices in the description aren't phone numbers
    no_phone = dict(event, description="Paid on 2026-10-01")
    assert parse_event(no_phone, "55").phone_number is None


def test_parse_event_prefers_app_client_id():
    event = {
        "id": "e3",
        "summary": "Haircut (Bob)",
        "start": {"dateTime": "2026-10-01T12:00:00Z"},
        "end": {"dateTime": "2026-10-01T12:30:00Z"},
        "extendedProperties": {"private": {"client_id": "42", "service_type": "Fade"}},
    }
    parsed = parse_event(event)
    assert parsed.client_id == 42 and parsed.service_type == "Fade"


def test_analyze_frequency():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    regular = [base + timedelta(days=28 * i) for i in range(6)]
    avg, confidence = analyze_frequency(regular)
    assert avg == 28 and confidence == 1.0
    avg, confidence = analyze_frequency([base, base + timedelta(days=10), base + timedelta(days=60)])
    assert avg == 30 and confidence < 0.5
    assert analyze_frequency([base, base + timedelta(hours=2)]) is None  # same day counts once


def test_free_slots_respect_hours_busy_and_notice():
    day = date(2026, 10, 14)  # Wednesday
    tz = ZoneInfo(SP)
    busy = [(datetime(2026, 10, 14, 10, 0, tzinfo=tz), datetime(2026, 10, 14, 11, 0, tzinfo=tz))]
    now = datetime(2026, 10, 14, 8, 30, tzinfo=tz)
    slots = free_slots(day, DEFAULT_WORKING_HOURS, SP, 30, busy, now, min_notice_minutes=60)
    times = [s.strftime("%H:%M") for s in slots]
    assert times[0] == "09:30"  # 09:00 is inside the notice window
    assert "10:00" not in times and "10:30" not in times and "11:00" in times
    assert times[-1] == "17:30"
    assert free_slots(date(2026, 10, 18), DEFAULT_WORKING_HOURS, SP, 30, [], now) == []  # Sunday closed


def test_is_slot_free():
    tz = ZoneInfo(SP)
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert is_slot_free(datetime(2026, 10, 14, 15, 0, tzinfo=tz), DEFAULT_WORKING_HOURS, SP, 30, [], now)
    assert not is_slot_free(datetime(2026, 10, 14, 17, 45, tzinfo=tz), DEFAULT_WORKING_HOURS, SP, 30, [], now)
    assert not is_slot_free(datetime(2026, 10, 14, 7, 0, tzinfo=tz), DEFAULT_WORKING_HOURS, SP, 30, [], now)


def test_security_helpers():
    hashed = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", hashed) and not verify_password("wrong", hashed)
    assert decode_access_token(create_access_token(7)) == 7
    assert decode_access_token("garbage") is None
    assert decrypt_json(encrypt_json({"a": 1})) == {"a": 1}


def test_oauth_state_is_tamper_proof():
    state = encrypt_json({"business_id": 3, "verifier": "v", "purpose": "google_oauth"})
    assert parse_oauth_state(state) == (3, "v")
    assert parse_oauth_state(state[:-4] + "AAAA") is None
    assert parse_oauth_state(encrypt_json({"business_id": 3, "verifier": "v", "purpose": "other"})) is None
