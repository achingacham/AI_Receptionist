import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
import httpx
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .. import storage
from ..receptionist import chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    scenario: str = "general"
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, http_request: Request):
    if not getattr(http_request.app.state, "ready", True):
        raise HTTPException(
            status_code=503,
            detail={
                "detail": "Upstream AI provider unavailable",
                "error_code": "UPSTREAM_UNAVAILABLE",
            },
        )

    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    session_id = request.session_id or str(uuid.uuid4())
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = chat(messages, scenario=request.scenario)
    except httpx.HTTPStatusError as e:
        logger.exception("Upstream HTTPStatusError from LLM provider: %s", e)
        raise HTTPException(
            status_code=502,
            detail={
                "detail": f"Upstream provider error: {e}",
                "error_code": "UPSTREAM_PROVIDER_ERROR",
            },
        ) from e
    except Exception as e:
        logger.exception("Unexpected error in chat endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    last_message = request.messages[-1]
    await run_in_threadpool(
        storage.record_turn, "chat", session_id, last_message.role, last_message.content
    )
    await run_in_threadpool(storage.record_turn, "chat", session_id, "assistant", reply)

    return ChatResponse(reply=reply, session_id=session_id)
