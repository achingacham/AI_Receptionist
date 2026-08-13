import asyncio

from fastapi.testclient import TestClient

from backend.app.main import app
import backend.app.routes.voice_daily as voice_daily
from backend.app.voice.pipeline import build_greeting_frame, settings as voice_settings

client = TestClient(app)

async def dummy_run_daily_bot(room_url: str, token: str):
    return None

async def dummy_daily_post(path: str, body: dict):
    if path == "/rooms":
        return {"url": "https://test.daily.co/testroom", "name": "testroom"}
    if path == "/meeting-tokens":
        if body["properties"].get("is_owner"):
            return {"token": "fake-bot-token"}
        return {"token": "fake-user-token"}
    raise ValueError(f"Unexpected path: {path}")


def dummy_create_task(coro):
    loop = asyncio.get_running_loop()
    return loop.create_task(coro)


def test_start_voice_call_creates_room_and_tokens(monkeypatch):
    monkeypatch.setattr(voice_daily.settings, "daily_api_key", "dummy-key")
    monkeypatch.setattr(voice_daily, "_daily_post", dummy_daily_post)
    monkeypatch.setattr(voice_daily, "run_daily_bot", dummy_run_daily_bot)
    monkeypatch.setattr(voice_daily.asyncio, "create_task", dummy_create_task)

    response = client.post("/api/voice/start")

    assert response.status_code == 200
    payload = response.json()
    assert payload["room_url"] == "https://test.daily.co/testroom"
    assert payload["token"] == "fake-user-token"


def test_build_greeting_frame_uses_receptionist_and_business_name():
    # Ensure the greeting frame is constructed with expected text
    voice_settings.receptionist_name = "Test Receptionist"
    voice_settings.business_name = "Test Business"

    frame = build_greeting_frame()
    assert frame.text == "Hello, this is Test Receptionist from Test Business. How can I help you today?"


def test_start_voice_call_requires_daily_api_key(monkeypatch):
    monkeypatch.setattr(voice_daily.settings, "daily_api_key", "")

    response = client.post("/api/voice/start")

    assert response.status_code == 503
    assert response.json()["detail"] == "DAILY_API_KEY not configured"
