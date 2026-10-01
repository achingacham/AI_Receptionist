"""Shared appointment-intent extraction and Cal.com action execution.

Used by both the appointment endpoint and the general chat endpoint so any
conversation can trigger a real calendar action when the caller expresses
booking/rescheduling/cancellation/availability intent.
"""

import json
import re
from datetime import date

from .config import settings
from .llm_client import LLMClient
from . import cal_com_client as cal

client = LLMClient(
    api_key=settings.llm_api_key or "",
    api_url=settings.llm_api_url,
    model=settings.llm_model,
)

INTENT_EXTRACTION_PROMPT = """You are an intent extractor for a medical clinic receptionist chatbot.

Given the conversation below, extract the user's appointment intent as JSON.

Return ONLY valid JSON — no explanation, no markdown. Use this schema:
{
  "action": "book" | "reschedule" | "cancel" | "check_availability" | "none",
  "appointment_type": string | null,
  "date": "YYYY-MM-DD" | null,
  "time": "HH:MM" | null,
  "duration_minutes": integer | null,
  "attendee_name": string | null,
  "attendee_email": string | null,
  "existing_date": "YYYY-MM-DD" | null,
  "event_id": string | null
}

If information is missing or unclear, set the field to null.
Today's date for reference: __TODAY__

Conversation:
__CONVERSATION__
"""


def _extract_intent(messages: list[dict]) -> dict:
    today = date.today().isoformat()
    conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    prompt = INTENT_EXTRACTION_PROMPT.replace("__TODAY__", today).replace(
        "__CONVERSATION__", conversation
    )

    raw = client.generate(
        f"SYSTEM:\nYou extract structured JSON from conversations. Output only JSON.\n\nUSER:\n{prompt}",
        max_tokens=512,
    )

    # Extract JSON from the response (strip any markdown code fences)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {"action": "none"}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {"action": "none"}


def _format_slots(slots: list[dict]) -> str:
    if not slots:
        return "no available slots"
    return ", ".join(s["display"] for s in slots[:5])


def get_calendar_context(messages: list[dict]) -> str:
    """Extract appointment intent and execute the corresponding Cal.com action.

    Returns a description of the calendar system's response, for injection into
    an LLM system prompt — or "" if the conversation has no calendar intent.
    """
    intent = _extract_intent(messages)
    action = intent.get("action", "none")
    calendar_context = ""

    if action == "check_availability":
        date_str = intent.get("date")
        if date_str:
            try:
                slots = cal.get_available_slots(
                    date_str, duration_minutes=intent.get("duration_minutes") or 30
                )
                calendar_context = (
                    f"[Calendar] Available slots on {date_str}: {_format_slots(slots)}"
                )
            except Exception as e:
                calendar_context = f"[Calendar] Could not fetch availability: {e}"

    elif action == "book":
        date_str = intent.get("date")
        time_str = intent.get("time")
        name = intent.get("attendee_name")
        appt_type = intent.get("appointment_type") or "Appointment"
        duration = intent.get("duration_minutes") or 30

        if date_str and time_str and name:
            try:
                event = cal.book_appointment(
                    summary=appt_type,
                    date_str=date_str,
                    time_str=time_str,
                    duration_minutes=duration,
                    attendee_name=name,
                    attendee_email=intent.get("attendee_email"),
                )
                calendar_context = (
                    f"[Calendar] Appointment successfully booked. "
                    f"Booking UID: {event['uid']}. Date: {date_str}, Time: {time_str}, "
                    f"Type: {appt_type}, Name: {name}."
                )
            except Exception as e:
                calendar_context = f"[Calendar] Booking failed: {e}"
        else:
            missing = [
                f for f, v in [("date", date_str), ("time", time_str), ("name", name)] if not v
            ]
            calendar_context = f"[Calendar] Cannot book — missing: {', '.join(missing)}."

    elif action == "reschedule":
        event_id = intent.get("event_id")
        existing_date = intent.get("existing_date")
        name = intent.get("attendee_name")
        new_date = intent.get("date")
        new_time = intent.get("time")
        duration = intent.get("duration_minutes") or 30

        if not event_id and existing_date and name:
            try:
                event = cal.find_booking_by_name_and_date(name, existing_date)
                event_id = event["uid"] if event else None
            except Exception:
                event_id = None

        if event_id and new_date and new_time:
            try:
                cal.reschedule_appointment(event_id, new_date, new_time, duration)
                calendar_context = (
                    f"[Calendar] Appointment rescheduled. "
                    f"New date: {new_date}, New time: {new_time}."
                )
            except Exception as e:
                calendar_context = f"[Calendar] Reschedule failed: {e}"
        else:
            calendar_context = "[Calendar] Cannot reschedule — need existing appointment details and new date/time."

    elif action == "cancel":
        event_id = intent.get("event_id")
        existing_date = intent.get("existing_date")
        name = intent.get("attendee_name")

        if not event_id and existing_date and name:
            try:
                event = cal.find_booking_by_name_and_date(name, existing_date)
                event_id = event["uid"] if event else None
            except Exception:
                event_id = None

        if event_id:
            try:
                cal.cancel_appointment(event_id)
                calendar_context = "[Calendar] Appointment canceled successfully."
            except Exception as e:
                calendar_context = f"[Calendar] Cancellation failed: {e}"
        else:
            calendar_context = "[Calendar] Could not find the appointment to cancel."

    return calendar_context
