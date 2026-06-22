"""Dedicated Twilio endpoints at /twilio/* (always active regardless of VOICE_PROVIDER)."""

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response

from ..config import settings
from ..voice.twilio_bot import run_twilio_bot

router = APIRouter(prefix="/twilio", tags=["twilio"])


@router.post("/incoming")
async def twilio_incoming(request: Request):
    """Twilio webhook — returns TwiML to open a Media Stream."""
    host = request.headers.get("host", "localhost")
    # Azure Container Apps terminates TLS — scheme inside the container is always
    # http, but the external URL is always https, so always use wss://.
    stream_url = f"wss://{host}/twilio/stream"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Aditi" language="en-IN">
    Welcome to {settings.business_name}. Please hold while I connect you to {settings.receptionist_name}.
  </Say>
  <Connect>
    <Stream url="{stream_url}" />
  </Connect>
</Response>"""

    return Response(content=xml, media_type="application/xml")


@router.websocket("/stream")
async def twilio_stream(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Streams bidirectional audio."""
    await websocket.accept()
    try:
        start_msg = await websocket.receive_json()
        stream_sid = (
            start_msg.get("start", {}).get("streamSid")
            or start_msg.get("streamSid", "unknown")
        )
        call_sid = start_msg.get("start", {}).get("callSid", "")
        account_sid = start_msg.get("start", {}).get("accountSid", "")
    except Exception:
        stream_sid = "unknown"
        call_sid = ""
        account_sid = ""
    
    auth_token = settings.twilio_auth_token or ""
    await run_twilio_bot(websocket, stream_sid, call_sid, account_sid, auth_token)
