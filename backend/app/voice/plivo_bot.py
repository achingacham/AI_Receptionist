"""Plivo transport bot using Pipecat + Sarvam STT/TTS + Groq LLM."""

from loguru import logger

from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.llm_response_universal import LLMRunFrame
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from starlette.websockets import WebSocket

from .pipeline import build_pipeline


async def run_plivo_bot(websocket: WebSocket, stream_id: str):
    """Handle a single Plivo call via Pipecat pipeline."""

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            add_wav_header=False,
            serializer=PlivoFrameSerializer(stream_id=stream_id),
        ),
    )

    task, context = build_pipeline(transport)

    @transport.event_handler("on_client_connected")
    async def on_connected(transport, client):
        logger.info(f"Plivo call connected — stream_id={stream_id}")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        logger.info("Plivo call disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
