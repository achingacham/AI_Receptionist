"""Direct Sarvam STT → LLM → Sarvam TTS endpoint for browser-based testing.

No Twilio or telephony required. The browser records WAV audio, POSTs it here,
and gets back a JSON payload with the transcript, LLM reply, and base64 audio.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
import httpx

from ..config import settings
from ..receptionist import build_system_prompt, client as llm_client

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
            raise HTTPException(
                status_code=400, detail="Could not transcribe audio — is the microphone working?"
            )

        # ── 2. LLM ───────────────────────────────────────────────────────────
        system_prompt = build_system_prompt("appointment") + _VOICE_SYSTEM_SUFFIX
        try:
            reply = llm_client.generate(
                f"SYSTEM: {system_prompt}\nUSER: {transcript}", max_tokens=150
            ).strip()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM error {e.response.status_code}: {e.response.text}",
            ) from e

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
