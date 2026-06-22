"""Pipecat voice bot: Plivo WebSocket transport + Sarvam STT/TTS + Groq LLM."""

from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContext,
    LLMContextAggregatorPair,
)
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from starlette.websockets import WebSocket

from ..config import settings
from ..receptionist import build_system_prompt


async def run_bot(websocket: WebSocket, stream_id: str):
    """Run the Pipecat pipeline for a single Plivo call."""

    serializer = PlivoFrameSerializer(stream_id=stream_id)

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    stt = SarvamSTTService(
        api_key=settings.sarvam_api_key,
        model="saaras:v2",
        sample_rate=8000,
        input_audio_codec="mulaw",
    )

    llm = OpenAILLMService(
        api_key=settings.groq_api_key or "",
        model=settings.groq_model,
        base_url=settings.groq_api_url,
    )

    tts = SarvamTTSService(
        api_key=settings.sarvam_api_key,
        sample_rate=8000,
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

    @transport.event_handler("on_client_connected")
    async def on_connected(transport, client):
        logger.info("Plivo call connected")
        from pipecat.processors.aggregators.llm_response_universal import LLMRunFrame
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        logger.info("Plivo call disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
