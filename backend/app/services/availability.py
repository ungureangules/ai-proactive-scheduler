from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC (some DB drivers drop tzinfo) and normalise to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def working_window(day: date, working_hours: dict, tz: ZoneInfo) -> tuple[datetime, datetime] | None:
    hours = (working_hours or {}).get(WEEKDAYS[day.weekday()])
    if not hours or not hours.get("start") or not hours.get("end"):
        return None
    start = datetime.combine(day, time.fromisoformat(hours["start"]), tzinfo=tz)
    end = datetime.combine(day, time.fromisoformat(hours["end"]), tzinfo=tz)
    if end <= start:
        return None
    return start, end


def free_slots(
    day: date,
    working_hours: dict,
    tz_name: str,
    duration_minutes: int,
    busy: list[tuple[datetime, datetime]],
    now: datetime,
    min_notice_minutes: int = 0,
) -> list[datetime]:
    """Start times (aware, in the business timezone) of free slots on `day`."""
    tz = ZoneInfo(tz_name)
    window = working_window(day, working_hours, tz)
    if window is None:
        return []
    start, end = window
    duration = timedelta(minutes=duration_minutes)
    earliest = as_utc(now) + timedelta(minutes=min_notice_minutes)
    busy_utc = [(as_utc(b_start), as_utc(b_end)) for b_start, b_end in busy]

    slots = []
    slot = start
    while slot + duration <= end:
        slot_utc = slot.astimezone(timezone.utc)
        slot_end_utc = slot_utc + duration
        overlaps = any(b_start < slot_end_utc and slot_utc < b_end for b_start, b_end in busy_utc)
        if slot_utc >= earliest and not overlaps:
            slots.append(slot)
        slot += duration
    return slots


def is_slot_free(
    start: datetime,
    working_hours: dict,
    tz_name: str,
    duration_minutes: int,
    busy: list[tuple[datetime, datetime]],
    now: datetime,
    min_notice_minutes: int = 0,
) -> bool:
    tz = ZoneInfo(tz_name)
    local = start.astimezone(tz)
    window = working_window(local.date(), working_hours, tz)
    if window is None:
        return False
    end = local + timedelta(minutes=duration_minutes)
    if local < window[0] or end > window[1]:
        return False
    if as_utc(local) < as_utc(now) + timedelta(minutes=min_notice_minutes):
        return False
    return not any(as_utc(b_start) < as_utc(end) and as_utc(local) < as_utc(b_end) for b_start, b_end in busy)
