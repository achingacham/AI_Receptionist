from fastapi.testclient import TestClient

from backend.app.main import app
import backend.app.receptionist as receptionist
import backend.app.routes.chat as chat_route

client = TestClient(app)


def test_build_system_prompt_injects_settings(monkeypatch):
    monkeypatch.setattr(receptionist.settings, "receptionist_name", "Alex")
    monkeypatch.setattr(receptionist.settings, "business_name", "Acme Dental")
    monkeypatch.setattr(receptionist.settings, "business_hours", "9am - 5pm")

    prompt = receptionist.build_system_prompt(scenario="general")

    assert "Alex" in prompt
    assert "Acme Dental" in prompt
    assert "9am - 5pm" in prompt


def test_receptionist_chat_calls_llm(monkeypatch):
    monkeypatch.setattr(receptionist, "get_calendar_context", lambda messages: None)

    captured_prompt = {}

    def mock_generate(prompt: str, max_tokens: int = 1024):
        captured_prompt["text"] = prompt
        return "Hello! How can I assist you today?"

    monkeypatch.setattr(receptionist.client, "generate", mock_generate)

    messages = [{"role": "user", "content": "What are your hours?"}]
    reply = receptionist.chat(messages, scenario="general")

    assert reply == "Hello! How can I assist you today?"
    assert "USER: What are your hours?" in captured_prompt["text"]
    assert "SYSTEM:" in captured_prompt["text"]


def test_chat_endpoint_empty_messages():
    response = client.post("/api/chat", json={"messages": []})
    assert response.status_code == 400
    assert response.json()["detail"] == "No messages provided"


def test_chat_endpoint_success(monkeypatch):
    monkeypatch.setattr(
        chat_route, "chat", lambda messages, scenario="general": "Sure, we are open 9am to 5pm."
    )
    monkeypatch.setattr(chat_route.storage, "record_turn", lambda *args, **kwargs: None)

    payload = {
        "messages": [{"role": "user", "content": "When do you open?"}],
        "scenario": "general",
        "session_id": "test-session-123",
    }
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Sure, we are open 9am to 5pm."
    assert data["session_id"] == "test-session-123"


def test_chat_endpoint_generates_session_id(monkeypatch):
    monkeypatch.setattr(chat_route, "chat", lambda messages, scenario="general": "Automated reply")
    monkeypatch.setattr(chat_route.storage, "record_turn", lambda *args, **kwargs: None)

    payload = {
        "messages": [{"role": "user", "content": "Hi there!"}],
    }
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["reply"] == "Automated reply"
    assert len(data["session_id"]) > 0


def test_chat_endpoint_degraded_preflight_fast_fails(monkeypatch):
    monkeypatch.setattr(app.state, "ready", False)

    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 503
    payload = response.json()["detail"]
    assert payload["error_code"] == "UPSTREAM_UNAVAILABLE"


def test_chat_endpoint_upstream_http_status_error(monkeypatch):
    import httpx

    def mock_chat_raise(messages, scenario="general"):
        req = httpx.Request("POST", "https://api.example.com/chat/completions")
        resp = httpx.Response(404, request=req)
        raise httpx.HTTPStatusError("DeploymentNotFound", request=req, response=resp)

    monkeypatch.setattr(chat_route, "chat", mock_chat_raise)
    monkeypatch.setattr(app.state, "ready", True)

    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 502
    payload = response.json()["detail"]
    assert payload["error_code"] == "UPSTREAM_PROVIDER_ERROR"


def test_health_endpoint_reports_degraded(monkeypatch):
    monkeypatch.setattr(app.state, "ready", False)
    monkeypatch.setattr(app.state, "preflight_error", "DeploymentNotFound")

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "DeploymentNotFound" in data["error"]
