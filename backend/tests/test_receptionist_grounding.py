from backend.app.receptionist import build_system_prompt, chat
from backend.app.safety import EMERGENCY_CIRCUIT_BREAKER_RESPONSE


def test_build_system_prompt_includes_schedule_and_knowledge():
    prompt = build_system_prompt("general")
    assert "CLINIC SCHEDULE & OPERATING STATUS:" in prompt
    assert "CLINIC KNOWLEDGE BASE (GROUNDING SOURCE OF TRUTH):" in prompt
    assert "GROUNDING GUARDRAIL DIRECTIVES:" in prompt
    assert "Magnus Hearing and Speech Clinic" in prompt
    assert "STRICT FACTUAL BOUNDARY" in prompt


def test_chat_trips_safety_circuit_breaker_without_llm():
    messages = [
        {
            "role": "user",
            "content": "I suddenly lost hearing in my right ear and it feels completely dead",
        }
    ]
    response = chat(messages)
    assert response == EMERGENCY_CIRCUIT_BREAKER_RESPONSE


def test_chat_with_mocked_llm(monkeypatch):
    import backend.app.receptionist as rec

    monkeypatch.setattr(
        rec.client, "generate", lambda prompt, max_tokens: "Hello, how can I help you today?"
    )
    messages = [{"role": "user", "content": "Hello, what are your fees?"}]
    response = chat(messages)
    assert response == "Hello, how can I help you today?"
