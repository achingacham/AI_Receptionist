import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app

client = TestClient(app)


# ── Hermetic Unit Tests (Offline / CI) ──────────────────────────────────────────


def test_local_health_endpoint_ok(monkeypatch):
    """Hermetic unit test: verifies /health returns 200 OK when app.state.ready is True."""
    monkeypatch.setattr(app.state, "ready", True)
    monkeypatch.setattr(settings, "business_name", "Magnus Hearing and Speech Clinic")
    monkeypatch.setattr(settings, "receptionist_name", "Arya")

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["business"] == "Magnus Hearing and Speech Clinic"
    assert data["receptionist"] == "Arya"


def test_local_health_endpoint_degraded(monkeypatch):
    """Hermetic unit test: verifies /health returns 503 when app.state.ready is False."""
    monkeypatch.setattr(app.state, "ready", False)
    monkeypatch.setattr(app.state, "preflight_error", "Upstream AI provider not ready")

    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data


# ── Live Integration / Public Site Smoke Tests ────────────────────────────────


@pytest.mark.integration
def test_live_public_site_health():
    """Live smoke test: verifies public HTTPS health endpoint on the live domain."""
    domain = settings.domain or "aireceptionist.aevum-intel.com"
    url = f"https://{domain}/health"

    with httpx.Client(timeout=10.0, follow_redirects=True) as http_client:
        response = http_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "business" in data
    assert "receptionist" in data


@pytest.mark.integration
def test_live_public_site_homepage():
    """Live smoke test: verifies public HTTPS homepage serves the web chat client."""
    domain = settings.domain or "aireceptionist.aevum-intel.com"
    url = f"https://{domain}/"

    with httpx.Client(timeout=10.0, follow_redirects=True) as http_client:
        response = http_client.get(url)

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "<title>AI Receptionist</title>" in response.text
    assert 'id="chat-window"' in response.text
