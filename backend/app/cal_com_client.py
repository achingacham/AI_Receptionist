"""Cal.com API v2 client for booking, rescheduling, and canceling appointments."""

from datetime import datetime, timezone
from typing import Optional
import httpx

from .config import settings

_BASE_URL = "https://api.cal.com/v2"
_API_VERSION = "2024-08-13"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.calcom_api_key}",
        "cal-api-version": _API_VERSION,
        "Content-Type": "application/json",
    }


def _to_utc_iso(date_str: str, time_str: str) -> str:
    """Combine YYYY-MM-DD and HH:MM in the configured timezone, return UTC ISO string."""
    import zoneinfo
    tz = zoneinfo.ZoneInfo(settings.calcom_timezone)
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=tz).astimezone(timezone.utc).isoformat()


def get_available_slots(date_str: str, duration_minutes: int = 30) -> list[dict]:
    """Return available slots on a given date (YYYY-MM-DD) from Cal.com."""
    import zoneinfo
    tz = zoneinfo.ZoneInfo(settings.calcom_timezone)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    day_start = date.replace(hour=0, minute=0, second=0, tzinfo=tz).astimezone(timezone.utc)
    day_end = date.replace(hour=23, minute=59, second=59, tzinfo=tz).astimezone(timezone.utc)

    params = {
        "startTime": day_start.isoformat(),
        "endTime": day_end.isoformat(),
        "eventTypeId": settings.calcom_event_type_id,
        "username": settings.calcom_username,
    }
    resp = httpx.get(f"{_BASE_URL}/slots/available", headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    slots_by_date = resp.json().get("data", {}).get("slots", {})
    raw_slots = slots_by_date.get(date_str, [])

    results = []
    for slot in raw_slots:
        slot_utc = datetime.fromisoformat(slot["time"].replace("Z", "+00:00"))
        slot_local = slot_utc.astimezone(tz)
        results.append({
            "start": slot["time"],
            "display": slot_local.strftime("%I:%M %p"),
        })
    return results


def book_appointment(
    summary: str,
    date_str: str,
    time_str: str,
    duration_minutes: int,
    attendee_name: str,
    attendee_email: Optional[str],
) -> dict:
    """Create a Cal.com booking and return the booking dict (contains uid)."""
    payload = {
        "start": _to_utc_iso(date_str, time_str),
        "eventTypeId": settings.calcom_event_type_id,
        "attendee": {
            "name": attendee_name,
            "email": attendee_email or settings.calcom_fallback_email,
            "timeZone": settings.calcom_timezone,
        },
        "metadata": {"appointmentType": summary},
    }
    resp = httpx.post(f"{_BASE_URL}/bookings", headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json().get("data", {})


def find_booking_by_name_and_date(attendee_name: str, date_str: str) -> Optional[dict]:
    """Fetch bookings on a given date and match by attendee name client-side."""
    import zoneinfo
    tz = zoneinfo.ZoneInfo(settings.calcom_timezone)
    date = datetime.strptime(date_str, "%Y-%m-%d")
    after = date.replace(hour=0, minute=0, second=0, tzinfo=tz).astimezone(timezone.utc).isoformat()
    before = date.replace(hour=23, minute=59, second=59, tzinfo=tz).astimezone(timezone.utc).isoformat()

    params = {"afterStart": after, "beforeStart": before, "take": 50}
    resp = httpx.get(f"{_BASE_URL}/bookings", headers=_headers(), params=params, timeout=15)
    resp.raise_for_status()
    bookings = resp.json().get("data", {}).get("bookings", [])

    name_lower = attendee_name.lower()
    for booking in bookings:
        if any(name_lower in a.get("name", "").lower() for a in booking.get("attendees", [])):
            return booking
    return None


def reschedule_appointment(booking_uid: str, new_date_str: str, new_time_str: str, duration_minutes: int) -> dict:
    """Move an existing Cal.com booking to a new date/time."""
    payload = {
        "start": _to_utc_iso(new_date_str, new_time_str),
        "reschedulingReason": "Rescheduled via AI Receptionist",
    }
    resp = httpx.patch(
        f"{_BASE_URL}/bookings/{booking_uid}/reschedule",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("data", {})


def cancel_appointment(booking_uid: str) -> None:
    """Cancel a Cal.com booking."""
    payload = {"cancellationReason": "Canceled via AI Receptionist"}
    resp = httpx.post(
        f"{_BASE_URL}/bookings/{booking_uid}/cancel",
        headers=_headers(),
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
