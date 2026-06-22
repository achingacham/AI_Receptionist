"""Direct Sarvam STT → Groq LLM → Sarvam TTS endpoint for browser-based testing.

No Twilio or telephony required. The browser records WAV audio, POSTs it here,
and gets back a JSON payload with the transcript, LLM reply, and base64 audio.
"""

import base64
from fastapi import APIRouter, File, HTTPException, UploadFile
import httpx

from ..config import settings
from ..receptionist import build_system_prompt

router = APIRouter(prefix="/sarvam", tags=["sarvam-test"])

_SARVAM_STT = "https://api.sarvam.ai/speech-to-text"
_SARVAM_TTS = "https://api.sarvam.ai/text-to-speech"

_VOICE_SYSTEM_SUFFIX = (
    "\n\nIMPORTANT: You are on a voice call. Keep responses SHORT — 1-2 sentences. "
    "No bullet points or markdown. Ask only one question at a time."
)


@router.post("/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):
    """Accept a WAV audio file, run STT → LLM → TTS, return transcript + reply + audio."""
    audio_bytes = await audio.read()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ── 1. Sarvam STT ────────────────────────────────────────────────────
        stt_resp = await client.post(
            _SARVAM_STT,
            headers={"api-subscription-key": settings.sarvam_api_key},
            files={"file": ("audio.wav", audio_bytes, "audio/wav")},
            data={"model": "saaras:v2", "language_code": "en-IN"},
        )
        if stt_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Sarvam STT error {stt_resp.status_code}: {stt_resp.text}",
            )
        transcript = stt_resp.json().get("transcript", "").strip()
        if not transcript:
            raise HTTPException(status_code=400, detail="Could not transcribe audio — is the microphone working?")

        # ── 2. Groq LLM ──────────────────────────────────────────────────────
        system_prompt = build_system_prompt("appointment") + _VOICE_SYSTEM_SUFFIX
        llm_resp = await client.post(
            f"{settings.groq_api_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcript},
                ],
                "max_tokens": 150,
                "temperature": 0.7,
            },
        )
        if llm_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Groq LLM error {llm_resp.status_code}: {llm_resp.text}",
            )
        reply = llm_resp.json()["choices"][0]["message"]["content"].strip()

        # ── 3. Sarvam TTS ────────────────────────────────────────────────────
        tts_resp = await client.post(
            _SARVAM_TTS,
            headers={"api-subscription-key": settings.sarvam_api_key},
            json={
                "inputs": [reply],
                "target_language_code": "en-IN",
                "speaker": "meera",
                "model": "bulbul:v2",
                "enable_preprocessing": True,
            },
        )
        if tts_resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Sarvam TTS error {tts_resp.status_code}: {tts_resp.text}",
            )
        audio_b64 = tts_resp.json()["audios"][0]

    return {
        "transcript": transcript,
        "reply": reply,
        "audio": audio_b64,  # base64-encoded WAV
    }
