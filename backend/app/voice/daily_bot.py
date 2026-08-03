"""Pipecat bot that joins a Daily.co room and runs the STT→LLM→TTS pipeline.

Requires daily-python SDK (not on public PyPI — install from Daily.co's index).
"""
import asyncio

from starlette.concurrency import run_in_threadpool

from .. import storage


async def run_daily_bot(room_url: str, token: str):
    try:
        from pipecat.transports.daily.transport import DailyParams, DailyTransport
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.pipeline.runner import PipelineRunner
        from .pipeline import build_pipeline
    except Exception as e:
        raise RuntimeError(
            "daily-python SDK not installed. "
            "See https://docs.daily.co/reference/python for installation."
        ) from e

    transport = DailyTransport(
        room_url,
        token,
        "Kiran",
        DailyParams(
        audio_in_enabled=True,              # ← was missing; bot must receive caller audio
        audio_out_enabled=True,
        transcription_enabled=False,         # keep OFF — Sarvam does STT, and Daily's is the paid trigger
        vad_analyzer=SileroVADAnalyzer(),    # turn detection for clean interruptions
   ),
    )
    task, context = build_pipeline(transport, sample_rate=16000, input_audio_codec="pcm")
    call_id = await run_in_threadpool(storage.start_call, "daily", room_url)

    @transport.event_handler("on_client_disconnected")
    async def on_disconnected(transport, client):
        await run_in_threadpool(storage.log_transcript, call_id, context.messages)
        await run_in_threadpool(storage.end_call, call_id)

    runner = PipelineRunner()
    await runner.run(task)
