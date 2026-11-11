"""Shared Pipecat pipeline: Sarvam STT → LLM → Sarvam TTS.

Transport-agnostic. Telephony bots (Plivo/Twilio/Exotel) use 8kHz mu-law;
browser (Daily.co) uses 16kHz PCM — pass sample_rate and input_audio_codec accordingly.
"""

import asyncio

from pipecat.pipeline.pipeline import Pipeline
from pipecat.frames.frames import Frame, LLMContextFrame, TextFrame
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContext,
    LLMContextAggregatorPair,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService

from ..calendar_intent import get_calendar_context
from ..config import settings
from ..receptionist import build_system_prompt
from ..safety import check_safety_circuit_breaker


class CalendarIntentProcessor(FrameProcessor):
    """Runs the same Cal.com intent-extraction used by text chat before each LLM
    turn, so voice calls get live calendar access instead of the LLM guessing at
    availability or hallucinating a booking confirmation.
    """

    def __init__(self, base_system_prompt: str):
        super().__init__()
        self._base_system_prompt = base_system_prompt

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMContextFrame) and direction == FrameDirection.DOWNSTREAM:
            messages = [m for m in frame.context.messages if m.get("role") != "system"]
            system_prompt = self._base_system_prompt
            if messages:
                # Fast check for Safety Perimeter Medical Circuit Breaker
                last_user_msg = messages[-1].get("content", "")
                circuit_breaker_override = check_safety_circuit_breaker(last_user_msg)
                if circuit_breaker_override:
                    system_prompt = (
                        "EMERGENCY PROTOCOL: You must immediately respond with this exact notice "
                        f"and nothing else: {circuit_breaker_override}"
                    )
                    frame.context.set_messages(
                        [{"role": "system", "content": system_prompt}, *messages]
                    )
                    await self.push_frame(frame, direction)
                    return

                calendar_context = await asyncio.to_thread(get_calendar_context, messages)
                if calendar_context:
                    system_prompt += (
                        f"\n\nCALENDAR / MESSAGE SYSTEM UPDATE:\n{calendar_context}\n"
                        "Use this information to respond to the client naturally."
                    )
            frame.context.set_messages([{"role": "system", "content": system_prompt}, *messages])

        await self.push_frame(frame, direction)


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
        model="saaras:v3",
        sample_rate=sample_rate,
        input_audio_codec=input_audio_codec,
    )

    llm = OpenAILLMService(
        api_key=settings.llm_api_key or "",
        model=settings.llm_model,
        base_url=settings.llm_api_url,
    )

    tts = SarvamTTSService(
        api_key=settings.sarvam_api_key,
        voice_id=settings.sarvam_tts_voice,
        sample_rate=sample_rate,
    )

    system_prompt = build_system_prompt("appointment")
    system_prompt += (
        "\n\nIMPORTANT: You are on a voice call. Keep responses SHORT — 1-2 sentences. "
        "No bullet points or markdown. Ask only one question at a time."
    )

    context = LLMContext(messages=[{"role": "system", "content": system_prompt}])
    context_aggregator = LLMContextAggregatorPair(context)
    calendar_intent = CalendarIntentProcessor(system_prompt)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            calendar_intent,
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(),
    )

    return task, context


def build_greeting_frame() -> TextFrame:
    """Build the voice greeting text frame for connected calls."""
    greeting = (
        f"Hello, this is {settings.receptionist_name} from {settings.business_name}. "
        "How can I help you today?"
    )
    return TextFrame(text=greeting)
