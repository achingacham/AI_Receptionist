"""Orchestrates appointment conversations: LLM extracts intent → calendar action → LLM reply."""

import json
import re
from typing import Optional

from .config import settings
from .groq_client import GroqClient
from .receptionist import build_system_prompt
from . import cal_com_client as cal

client = GroqClient(
    api_key=settings.groq_api_key or "",
    api_url=settings.groq_api_url,
    model=settings.groq_model,
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
    from datetime import date
    today = date.today().isoformat()
    conversation = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    prompt = INTENT_EXTRACTION_PROMPT.replace("__TODAY__", today).replace("__CONVERSATION__", conversation)

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


def handle_appointment(messages: list[dict]) -> str:
    """Main entry point: extract intent, execute calendar action, return natural language reply."""
    intent = _extract_intent(messages)
    action = intent.get("action", "none")
    calendar_context = ""

    if action == "check_availability":
        date = intent.get("date")
        if date:
            try:
                slots = cal.get_available_slots(date, duration_minutes=intent.get("duration_minutes") or 30)
                calendar_context = f"[Calendar] Available slots on {date}: {_format_slots(slots)}"
            except Exception as e:
                calendar_context = f"[Calendar] Could not fetch availability: {e}"

    elif action == "book":
        date = intent.get("date")
        time = intent.get("time")
        name = intent.get("attendee_name")
        appt_type = intent.get("appointment_type") or "Appointment"
        duration = intent.get("duration_minutes") or 30

        if date and time and name:
            try:
                event = cal.book_appointment(
                    summary=appt_type,
                    date_str=date,
                    time_str=time,
                    duration_minutes=duration,
                    attendee_name=name,
                    attendee_email=intent.get("attendee_email"),
                )
                calendar_context = (
                    f"[Calendar] Appointment successfully booked. "
                    f"Booking UID: {event['uid']}. Date: {date}, Time: {time}, "
                    f"Type: {appt_type}, Name: {name}."
                )
            except Exception as e:
                calendar_context = f"[Calendar] Booking failed: {e}"
        else:
            missing = [f for f, v in [("date", date), ("time", time), ("name", name)] if not v]
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
                updated = cal.reschedule_appointment(event_id, new_date, new_time, duration)
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
                calendar_context = f"[Calendar] Appointment canceled successfully."
            except Exception as e:
                calendar_context = f"[Calendar] Cancellation failed: {e}"
        else:
            calendar_context = "[Calendar] Could not find the appointment to cancel."

    # Build final prompt with calendar context injected into the system prompt
    system_prompt = build_system_prompt("appointment")
    if calendar_context:
        system_prompt += f"\n\nCALENDAR SYSTEM UPDATE:\n{calendar_context}\nUse this information to respond to the client naturally."

    prompt_parts = [f"SYSTEM:\n{system_prompt}", ""]
    for m in messages:
        role = m.get("role", "user").upper()
        prompt_parts.append(f"{role}: {m['content']}")
    prompt = "\n".join(prompt_parts)

    return client.generate(prompt, max_tokens=1024)
