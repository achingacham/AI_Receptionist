"""Dedicated Exotel endpoints at /exotel/* (always active regardless of VOICE_PROVIDER)."""

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response

from ..config import settings
from ..voice.exotel_bot import run_exotel_bot

router = APIRouter(prefix="/exotel", tags=["exotel"])


@router.post("/incoming")
async def exotel_incoming(request: Request):
    """Exotel webhook — returns TwiML to open a Media Stream."""
    host = request.headers.get("host", "localhost")
    # Azure Container Apps terminates TLS — scheme inside the container is always
    # http, but the external URL is always https, so always use wss://.
    stream_url = f"wss://{host}/exotel/stream"

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
async def exotel_stream(websocket: WebSocket):
    """WebSocket endpoint for Exotel Media Streams bidirectional audio."""
    await websocket.accept()
    try:
        start_msg = await websocket.receive_json()
        stream_sid = (
            start_msg.get("start", {}).get("streamSid")
            or start_msg.get("streamSid", "unknown")
        )
    except Exception:
        stream_sid = "unknown"
    await run_exotel_bot(websocket, stream_sid)
