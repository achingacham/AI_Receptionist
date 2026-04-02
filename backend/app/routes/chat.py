from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..receptionist import chat

router = APIRouter(prefix="/api", tags=["chat"])


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    scenario: str = "general"


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = chat(messages, scenario=request.scenario)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
