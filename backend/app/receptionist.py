from .calendar_intent import get_calendar_context
from .config import settings
from .knowledge import clinic_knowledge
from .llm_client import LLMClient
from .safety import check_safety_circuit_breaker
from .scenarios import SCENARIO_PROMPTS
from .schedule import clinic_schedule

# Initialize LLM client (requires LLM_API_KEY in env)
client = LLMClient(
    api_key=settings.llm_api_key or "", api_url=settings.llm_api_url, model=settings.llm_model
)


def build_system_prompt(scenario: str = "general", query: str | None = None) -> str:
    template = SCENARIO_PROMPTS.get(scenario, SCENARIO_PROMPTS["general"])
    prompt = template.format(
        name=settings.receptionist_name,
        business=settings.business_name,
        hours=settings.business_hours,
        phone=settings.business_phone or "Not provided",
        email=settings.business_email or "Not provided",
        address=settings.business_address or "Not provided",
    )

    # Inject deterministic Clinic Schedule
    schedule_context = clinic_schedule.get_prompt_context()
    if schedule_context:
        prompt += f"\n\n{schedule_context}"

    # Inject Clinic Knowledge Base and Grounding Guardrail
    knowledge_context = clinic_knowledge.get_grounding_context(query)
    if knowledge_context:
        prompt += f"\n\n{knowledge_context}"

    return prompt


def chat(messages: list[dict], scenario: str = "general") -> str:
    # Check Safety Perimeter & Medical Circuit Breaker on the latest user message
    user_messages = [m for m in messages if m.get("role") == "user"]
    last_user_text = user_messages[-1].get("content", "") if user_messages else ""
    circuit_breaker_override = check_safety_circuit_breaker(last_user_text)
    if circuit_breaker_override:
        return circuit_breaker_override

    # Dynamic query-aware knowledge or full in-context grounding
    system_prompt = build_system_prompt(scenario, query=last_user_text)

    # Intent extraction (Calendar actions or Caller Message capture)
    calendar_context = get_calendar_context(messages)
    if calendar_context:
        system_prompt += (
            f"\n\nCALENDAR / MESSAGE SYSTEM UPDATE:\n{calendar_context}\n"
            "Use this information to respond to the client naturally."
        )

    prompt_parts = ["SYSTEM:\n" + system_prompt, ""]
    for m in messages:
        role = m.get("role", "user").upper()
        content = m.get("content", "")
        prompt_parts.append(f"{role}: {content}")
    prompt = "\n".join(prompt_parts)

    return client.generate(prompt, max_tokens=1024)
