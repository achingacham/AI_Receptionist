"""Orchestrates appointment conversations: LLM extracts intent → calendar action → LLM reply."""

from .calendar_intent import get_calendar_context, client
from .receptionist import build_system_prompt


def handle_appointment(messages: list[dict]) -> str:
    """Main entry point: extract intent, execute calendar action, return natural language reply."""
    calendar_context = get_calendar_context(messages)

    system_prompt = build_system_prompt("appointment")
    if calendar_context:
        system_prompt += f"\n\nCALENDAR SYSTEM UPDATE:\n{calendar_context}\nUse this information to respond to the client naturally."

    prompt_parts = [f"SYSTEM:\n{system_prompt}", ""]
    for m in messages:
        role = m.get("role", "user").upper()
        prompt_parts.append(f"{role}: {m['content']}")
    prompt = "\n".join(prompt_parts)

    return client.generate(prompt, max_tokens=1024)
