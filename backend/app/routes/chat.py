import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .. import storage
from ..receptionist import chat

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
async def chat_endpoint(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    session_id = request.session_id or str(uuid.uuid4())
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = chat(messages, scenario=request.scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    last_message = request.messages[-1]
    await run_in_threadpool(storage.record_turn, "chat", session_id, last_message.role, last_message.content)
    await run_in_threadpool(storage.record_turn, "chat", session_id, "assistant", reply)

    return ChatResponse(reply=reply, session_id=session_id)
