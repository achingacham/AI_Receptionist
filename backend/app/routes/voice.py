"""Active voice provider endpoints at /call/*.

VOICE_PROVIDER=plivo   → delegates to Plivo bot
VOICE_PROVIDER=twilio  → delegates to Twilio bot
VOICE_PROVIDER=exotel  → delegates to Exotel bot
"""

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response

from ..config import settings

router = APIRouter(prefix="/call", tags=["voice"])


def _plivo_xml(host: str, scheme: str) -> str:
    stream_url = f"wss://{host}/call/stream"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Speak>
    Welcome to {settings.business_name}. Please hold while I connect you to {settings.receptionist_name}.
  </Speak>
  <Stream keepCallAlive="true" bidirectional="true" contentType="audio/x-mulaw;rate=8000" audioTrack="inbound">
    {stream_url}
  </Stream>
</Response>"""


def _twilio_xml(host: str, scheme: str) -> str:
    stream_url = f"wss://{host}/call/stream"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Aditi" language="en-IN">
    Welcome to {settings.business_name}. Please hold while I connect you to {settings.receptionist_name}.
  </Say>
  <Connect>
    <Stream url="{stream_url}" />
  </Connect>
</Response>"""


@router.post("/incoming")
async def call_incoming(request: Request):
    """Webhook called by the active voice provider when a call arrives."""
    host = request.headers.get("host", "localhost")
    scheme = request.url.scheme

    if settings.voice_provider == "twilio":
        xml = _twilio_xml(host, scheme)
    elif settings.voice_provider == "exotel":
        xml = _twilio_xml(host, scheme)
    else:
        xml = _plivo_xml(host, scheme)

    return Response(content=xml, media_type="application/xml")


@router.websocket("/stream")
async def call_stream(websocket: WebSocket):
    """WebSocket audio stream for the active voice provider."""
    if settings.voice_provider in ("twilio", "exotel"):
        from ..voice.twilio_bot import run_twilio_bot
        await websocket.accept()
        try:
            start_msg = await websocket.receive_json()
            stream_sid = (
                start_msg.get("start", {}).get("streamSid")
                or start_msg.get("streamSid", "unknown")
            )
        except Exception:
            stream_sid = "unknown"
        await run_twilio_bot(websocket, stream_sid)
    else:
        from ..voice.plivo_bot import run_plivo_bot
        await websocket.accept()
        try:
            start_msg = await websocket.receive_json()
            stream_id = (
                start_msg.get("start", {}).get("streamId")
                or start_msg.get("streamId", "unknown")
            )
        except Exception:
            stream_id = "unknown"
        await run_plivo_bot(websocket, stream_id)
