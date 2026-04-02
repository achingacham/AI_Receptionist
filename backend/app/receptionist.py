from .config import settings
from .groq_client import GroqClient
from .scenarios import SCENARIO_PROMPTS

# Initialize Groq client (requires GROQ_API_KEY in env)
client = GroqClient(api_key=settings.groq_api_key or "", api_url=settings.groq_api_url, model=settings.groq_model)


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
    prompt_parts = ["SYSTEM:\n" + build_system_prompt(scenario), ""]
    for m in messages:
        role = m.get("role", "user").upper()
        content = m.get("content", "")
        prompt_parts.append(f"{role}: {content}")
    prompt = "\n".join(prompt_parts)

    return client.generate(prompt, max_tokens=1024)
