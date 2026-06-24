"""Pipecat bot that joins a Daily.co room and runs the STT→LLM→TTS pipeline.

Requires daily-python SDK (not on public PyPI — install from Daily.co's index).
"""
import asyncio


async def run_daily_bot(room_url: str, token: str):
    try:
        from pipecat.transports.daily.transport import DailyParams, DailyTransport
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
        DailyParams(audio_out_enabled=True, transcription_enabled=False),
    )
    task, _ = build_pipeline(transport, sample_rate=16000, input_audio_codec="pcm")
    runner = PipelineRunner()
    await runner.run(task)
