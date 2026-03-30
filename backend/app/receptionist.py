from .config import settings
from .groq_client import GroqClient

# Initialize Groq client (requires GROQ_API_KEY in env)
client = GroqClient(api_key=settings.groq_api_key or "", api_url=settings.groq_api_url, model=settings.groq_model)

SYSTEM_PROMPT = """You are {name}, a professional AI receptionist for {business}.

Your responsibilities:
- Greet visitors and callers warmly and professionally
- Answer questions about the business (hours, location, services, contact info)
- Schedule appointments and take messages
- Direct inquiries to the appropriate department or person
- Handle common FAQs politely and efficiently
- Escalate urgent or complex issues appropriately

Business Information:
- Business Name: {business}
- Hours: {hours}
- Phone: {phone}
- Email: {email}
- Address: {address}

Guidelines:
- Always be polite, friendly, and professional
- Keep responses concise and helpful
- If you don't know something, offer to take a message or direct them appropriately
- Never make up information you don't have
- If asked about topics outside your receptionist role, gently redirect to business-related matters
"""


def build_system_prompt() -> str:
    return SYSTEM_PROMPT.format(
        name=settings.receptionist_name,
        business=settings.business_name,
        hours=settings.business_hours,
        phone=settings.business_phone or "Not provided",
        email=settings.business_email or "Not provided",
        address=settings.business_address or "Not provided",
    )


def chat(messages: list[dict]) -> str:
    # Convert role/content message list into a single prompt for Groq
    prompt_parts = ["SYSTEM:\n" + build_system_prompt(), ""]
    for m in messages:
        role = m.get("role", "user").upper()
        content = m.get("content", "")
        prompt_parts.append(f"{role}: {content}")
    prompt = "\n".join(prompt_parts)

    return client.generate(prompt, max_tokens=1024)
