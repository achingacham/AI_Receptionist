"""Exotel transport bot using Pipecat + Sarvam STT/TTS + Groq LLM."""

from loguru import logger

from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.llm_response_universal import LLMRunFrame
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from starlette.websockets import WebSocket

from .pipeline import build_pipeline


async def run_exotel_bot(websocket: WebSocket, stream_sid: str, call_sid: str = "", account_sid: str = "", auth_token: str = ""):
    """Handle a single Exotel call via Pipecat pipeline.
    
    Exotel uses the same Twilio-compatible TwiML format for Media Streams.
    """

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            add_wav_header=False,
            serializer=TwilioFrameSerializer(
                stream_sid=stream_sid,
                call_sid=call_sid,
                account_sid=account_sid,
                auth_token=auth_token,
                auto_hang_up=bool(call_sid and account_sid and auth_token),
            ),
        ),
    )

    task, context = build_pipeline(transport)

    @transport.event_handler("on_client_connected")
    async def on_connected(transport, client):
        logger.info(f"Exotel call connected — stream_sid={stream_sid}")
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        logger.info("Exotel call disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)
    await runner.run(task)
