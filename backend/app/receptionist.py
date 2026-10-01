from .calendar_intent import get_calendar_context
from .config import settings
from .llm_client import LLMClient
from .scenarios import SCENARIO_PROMPTS

# Initialize LLM client (requires LLM_API_KEY in env)
client = LLMClient(
    api_key=settings.llm_api_key or "", api_url=settings.llm_api_url, model=settings.llm_model
)


def build_system_prompt(scenario: str = "general") -> str:
    template = SCENARIO_PROMPTS.get(scenario, SCENARIO_PROMPTS["general"])
    return template.format(
        name=settings.receptionist_name,
        business=settings.business_name,
        hours=settings.business_hours,
        phone=settings.business_phone or "Not provided",
        email=settings.business_email or "Not provided",
        address=settings.business_address or "Not provided",
    )


def chat(messages: list[dict], scenario: str = "general") -> str:
    calendar_context = get_calendar_context(messages)

    system_prompt = build_system_prompt(scenario)
    if calendar_context:
        system_prompt += f"\n\nCALENDAR SYSTEM UPDATE:\n{calendar_context}\nUse this information to respond to the client naturally."

    prompt_parts = ["SYSTEM:\n" + system_prompt, ""]
    for m in messages:
        role = m.get("role", "user").upper()
        content = m.get("content", "")
        prompt_parts.append(f"{role}: {content}")
    prompt = "\n".join(prompt_parts)

    return client.generate(prompt, max_tokens=1024)
