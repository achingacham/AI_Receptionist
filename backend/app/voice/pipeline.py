"""Shared Pipecat pipeline: Sarvam STT → Groq LLM → Sarvam TTS.

Transport-agnostic. Telephony bots (Plivo/Twilio/Exotel) use 8kHz mu-law;
browser (Daily.co) uses 16kHz PCM — pass sample_rate and input_audio_codec accordingly.
"""

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContext,
    LLMContextAggregatorPair,
    LLMRunFrame,
)
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService

from ..config import settings
from ..receptionist import build_system_prompt


def build_pipeline(
    transport,
    sample_rate: int = 8000,
    input_audio_codec: str = "mulaw",
) -> tuple[PipelineTask, LLMContext]:
    """Build and return a PipelineTask + context for any Pipecat transport.

    Args:
        transport: A Pipecat transport (Plivo, Twilio, Exotel, or Daily).
        sample_rate: Audio sample rate in Hz. 8000 for telephony, 16000 for browser (Daily.co).
        input_audio_codec: Codec for STT input. "mulaw" for telephony, "pcm" for Daily.co.

    Returns:
        (task, context) — run task with PipelineRunner; context holds message history.
    """
    stt = SarvamSTTService(
        api_key=settings.sarvam_api_key,
        model="saaras:v2",
        sample_rate=sample_rate,
        input_audio_codec=input_audio_codec,
    )

    llm = OpenAILLMService(
        api_key=settings.groq_api_key or "",
        model=settings.groq_model,
        base_url=settings.groq_api_url,
    )

    tts = SarvamTTSService(
        api_key=settings.sarvam_api_key,
        sample_rate=sample_rate,
    )

    system_prompt = build_system_prompt("appointment")
    system_prompt += (
        "\n\nIMPORTANT: You are on a voice call. Keep responses SHORT — 1-2 sentences. "
        "No bullet points or markdown. Ask only one question at a time."
    )

    context = LLMContext(messages=[{"role": "system", "content": system_prompt}])
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        PipelineParams(allow_interruptions=True),
    )

    return task, context
