from contextlib import asynccontextmanager
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .config import settings
from .db import init_db
from .llm_client import LLMClient
from .routes.appointment import router as appointment_router
from .routes.chat import router as chat_router
from .routes.sarvam_test import router as sarvam_test_router
from .routes.voice import router as voice_router
from .routes.voice_daily import router as daily_voice_router
from .routes.voice_exotel import router as exotel_router
from .routes.voice_twilio import router as twilio_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Live Preflight Probe: verify upstream LLM provider readiness
    app.state.ready = True
    app.state.preflight_error = None
    if settings.llm_api_key:
        try:
            probe_client = LLMClient(
                api_key=settings.llm_api_key,
                api_url=settings.llm_api_url,
                model=settings.llm_model,
            )
            await run_in_threadpool(
                probe_client.generate,
                "SYSTEM:\nYou are a probe.\nUSER:\nSay pong",
                max_tokens=50,
            )
            logger.info(
                "Live preflight succeeded: LLM deployment '%s' is ready.", settings.llm_model
            )
        except Exception as exc:
            app.state.ready = False
            app.state.preflight_error = str(exc)
            logger.error(
                "FATAL: Live preflight failed for model '%s' at '%s': %s. Server degraded.",
                settings.llm_model,
                settings.llm_api_url,
                exc,
            )
    else:
        app.state.ready = False
        app.state.preflight_error = "LLM_API_KEY is not configured"
        logger.warning("FATAL: LLM_API_KEY is not configured. Server degraded.")

    yield


app = FastAPI(title="AI Receptionist", version="1.0.0", lifespan=lifespan)
app.state.ready = True
app.state.preflight_error = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(appointment_router)
app.include_router(voice_router)
app.include_router(twilio_router)
app.include_router(exotel_router)
app.include_router(sarvam_test_router)
app.include_router(daily_voice_router)


# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


@app.get("/health")
async def health():
    if not getattr(app.state, "ready", True):
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "error": getattr(app.state, "preflight_error", "Upstream AI provider not ready"),
                "business": settings.business_name,
                "receptionist": settings.receptionist_name,
            },
        )
    return {
        "status": "ok",
        "business": settings.business_name,
        "receptionist": settings.receptionist_name,
    }
