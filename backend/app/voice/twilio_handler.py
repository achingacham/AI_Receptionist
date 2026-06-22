"""Twilio Media Streams WebSocket handler.

Flow per call:
  Twilio → WebSocket (mulaw 8kHz) → STT (Sarvam) → LLM (Groq) → TTS (Sarvam) → WebSocket → Twilio
"""

import asyncio
import base64
import json
import struct
import io
from typing import Optional

import httpx
from fastapi import WebSocket

from ..config import settings
from ..appointment_handler import handle_appointment

# ── mulaw ↔ PCM conversion (audioop removed in Python 3.13) ──────────────────

_MULAW_BIAS = 0x84
_MULAW_CLIP = 32635

def _linear2ulaw(sample: int) -> int:
    sign = 0
    if sample < 0:
        sample = -sample
        sign = 0x80
    if sample > _MULAW_CLIP:
        sample = _MULAW_CLIP
    sample += _MULAW_BIAS
    exponent = 7
    for exp_lut in [0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x100,
                    0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x8000]:
        if sample <= exp_lut:
            break
        exponent -= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return (~(sign | (exponent << 4) | mantissa)) & 0xFF


def _ulaw2linear(u_val: int) -> int:
    u_val = ~u_val & 0xFF
    sign = u_val & 0x80
    exponent = (u_val >> 4) & 0x07
    mantissa = u_val & 0x0F
    sample = ((mantissa << 1) + 33) << (exponent + 2)
    return -sample if sign else sample


def mulaw_to_pcm16(mulaw_bytes: bytes) -> bytes:
    """Convert mulaw bytes to 16-bit signed PCM bytes."""
    samples = struct.pack(f"<{len(mulaw_bytes)}h",
                         *[_ulaw2linear(b) for b in mulaw_bytes])
    return samples


def pcm16_to_mulaw(pcm_bytes: bytes) -> bytes:
    """Convert 16-bit signed PCM bytes to mulaw bytes."""
    samples = struct.unpack(f"<{len(pcm_bytes)//2}h", pcm_bytes)
    return bytes([_linear2ulaw(s) for s in samples])


def build_wav(pcm_bytes: bytes, sample_rate: int = 8000, channels: int = 1) -> bytes:
    """Wrap raw PCM16 in a WAV container."""
    buf = io.BytesIO()
    data_len = len(pcm_bytes)
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_len))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
                          sample_rate * channels * 2, channels * 2, 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_len))
    buf.write(pcm_bytes)
    return buf.getvalue()


# ── Sarvam STT ────────────────────────────────────────────────────────────────

async def transcribe(wav_bytes: bytes) -> Optional[str]:
    """Send WAV audio to Sarvam STT and return transcript."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": settings.sarvam_api_key},
            files={"file": ("audio.wav", wav_bytes, "audio/wav")},
            data={"model": "saaras:v2", "language_code": "unknown"},
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("transcript", "").strip() or None


# ── Sarvam TTS ────────────────────────────────────────────────────────────────

async def synthesize(text: str) -> Optional[bytes]:
    """Convert text to mulaw 8kHz audio via Sarvam TTS."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "api-subscription-key": settings.sarvam_api_key,
                "Content-Type": "application/json",
            },
            json={
                "inputs": [text],
                "target_language_code": "en-IN",
                "speaker": "anushka",
                "model": "bulbul:v2",
                "speech_sample_rate": 8000,
                "encode_base64": False,
            },
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        audios = data.get("audios", [])
        if not audios:
            return None
        # Sarvam returns base64-encoded WAV
        wav_bytes = base64.b64decode(audios[0])
        # Strip WAV header (44 bytes) to get raw PCM, then convert to mulaw
        pcm_bytes = wav_bytes[44:]
        return pcm16_to_mulaw(pcm_bytes)


# ── Main WebSocket handler ────────────────────────────────────────────────────

# Silence threshold: stop buffering after ~800ms of no new audio
_SILENCE_TIMEOUT = 0.8
# Minimum audio to attempt STT (avoid transcribing short blips)
_MIN_AUDIO_BYTES = 3200   # ~200ms at 8kHz mulaw


async def handle_twilio_stream(websocket: WebSocket):
    """Handle a Twilio Media Stream WebSocket connection."""
    await websocket.accept()

    stream_sid: Optional[str] = None
    audio_buffer = bytearray()
    conversation: list[dict] = []
    last_audio_time = asyncio.get_event_loop().time()
    processing = False

    async def process_audio():
        nonlocal audio_buffer, processing, conversation
        processing = True
        chunk = bytes(audio_buffer)
        audio_buffer.clear()

        if len(chunk) < _MIN_AUDIO_BYTES:
            processing = False
            return

        # STT
        wav = build_wav(mulaw_to_pcm16(chunk), sample_rate=8000)
        transcript = await transcribe(wav)
        if not transcript:
            processing = False
            return

        # LLM via appointment handler
        conversation.append({"role": "user", "content": transcript})
        reply = handle_appointment(conversation)
        conversation.append({"role": "assistant", "content": reply})

        # TTS → send back to Twilio
        mulaw_audio = await synthesize(reply)
        if mulaw_audio and stream_sid:
            payload = base64.b64encode(mulaw_audio).decode()
            msg = json.dumps({
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": payload},
            })
            await websocket.send_text(msg)

        processing = False

    async def silence_watcher():
        nonlocal last_audio_time, processing
        while True:
            await asyncio.sleep(0.1)
            if (not processing and audio_buffer and
                    asyncio.get_event_loop().time() - last_audio_time > _SILENCE_TIMEOUT):
                await process_audio()

    watcher_task = asyncio.create_task(silence_watcher())

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            event = msg.get("event")

            if event == "start":
                stream_sid = msg["start"]["streamSid"]

            elif event == "media":
                payload = msg["media"]["payload"]
                chunk = base64.b64decode(payload)
                audio_buffer.extend(chunk)
                last_audio_time = asyncio.get_event_loop().time()

            elif event == "stop":
                break

    except Exception:
        pass
    finally:
        watcher_task.cancel()
        await websocket.close()
