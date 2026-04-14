"""Google Calendar client for booking, rescheduling, and canceling appointments."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    credentials = service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )
    delegated = credentials.with_subject(settings.google_calendar_owner_email)
    return build("calendar", "v3", credentials=delegated)


def get_available_slots(date_str: str, duration_minutes: int = 30) -> list[dict]:
    """Return free slots on a given date (YYYY-MM-DD) within business hours."""
    service = _get_service()
    calendar_id = settings.google_calendar_id

    # Parse date and define business-hours window (local naive → UTC)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    # Business hours from settings e.g. "Monday-Friday 10am-6:30pm" — use fixed window here
    day_start = date.replace(hour=10, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    day_end = date.replace(hour=18, minute=30, second=0, microsecond=0).astimezone(timezone.utc)

    body = {
        "timeMin": day_start.isoformat(),
        "timeMax": day_end.isoformat(),
        "items": [{"id": calendar_id}],
    }
    freebusy = service.freebusy().query(body=body).execute()
    busy_periods = freebusy["calendars"][calendar_id]["busy"]

    # Build all candidate slots
    slots = []
    cursor = day_start
    while cursor + timedelta(minutes=duration_minutes) <= day_end:
        slot_end = cursor + timedelta(minutes=duration_minutes)
        overlap = any(
            cursor < datetime.fromisoformat(b["end"]) and slot_end > datetime.fromisoformat(b["start"])
            for b in busy_periods
        )
        if not overlap:
            slots.append({
                "start": cursor.isoformat(),
                "end": slot_end.isoformat(),
                "display": cursor.strftime("%I:%M %p"),
            })
        cursor += timedelta(minutes=duration_minutes)

    return slots


def book_appointment(
    summary: str,
    date_str: str,
    time_str: str,
    duration_minutes: int,
    attendee_name: str,
    attendee_email: Optional[str],
) -> dict:
    """Create a calendar event and return the created event dict."""
    service = _get_service()
    calendar_id = settings.google_calendar_id

    dt_start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").astimezone(timezone.utc)
    dt_end = dt_start + timedelta(minutes=duration_minutes)

    event = {
        "summary": f"{summary} — {attendee_name}",
        "description": f"Booked via AI Receptionist for {attendee_name}",
        "start": {"dateTime": dt_start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": dt_end.isoformat(), "timeZone": "UTC"},
    }
    if attendee_email:
        event["attendees"] = [{"email": attendee_email}]

    created = service.events().insert(calendarId=calendar_id, body=event, sendUpdates="all").execute()
    return created


def find_event_by_name_and_date(attendee_name: str, date_str: str) -> Optional[dict]:
    """Find an event matching the attendee name on a given date."""
    service = _get_service()
    calendar_id = settings.google_calendar_id

    date = datetime.strptime(date_str, "%Y-%m-%d")
    time_min = date.replace(hour=0, minute=0, second=0).astimezone(timezone.utc).isoformat()
    time_max = date.replace(hour=23, minute=59, second=59).astimezone(timezone.utc).isoformat()

    events = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        q=attendee_name,
        singleEvents=True,
    ).execute()

    items = events.get("items", [])
    return items[0] if items else None


def reschedule_appointment(event_id: str, new_date_str: str, new_time_str: str, duration_minutes: int) -> dict:
    """Move an existing event to a new date/time."""
    service = _get_service()
    calendar_id = settings.google_calendar_id

    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    dt_start = datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M").astimezone(timezone.utc)
    dt_end = dt_start + timedelta(minutes=duration_minutes)

    event["start"] = {"dateTime": dt_start.isoformat(), "timeZone": "UTC"}
    event["end"] = {"dateTime": dt_end.isoformat(), "timeZone": "UTC"}

    updated = service.events().update(calendarId=calendar_id, eventId=event_id, body=event, sendUpdates="all").execute()
    return updated


def cancel_appointment(event_id: str) -> None:
    """Delete a calendar event."""
    service = _get_service()
    service.events().delete(calendarId=settings.google_calendar_id, eventId=event_id, sendUpdates="all").execute()
