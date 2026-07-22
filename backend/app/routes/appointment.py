import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from .. import storage
from ..appointment_handler import handle_appointment

router = APIRouter(prefix="/api", tags=["appointment"])


class Message(BaseModel):
    role: str
    content: str


class AppointmentRequest(BaseModel):
    messages: list[Message]
    session_id: str | None = None


class AppointmentResponse(BaseModel):
    reply: str
    session_id: str


@router.post("/appointment", response_model=AppointmentResponse)
async def appointment_endpoint(request: AppointmentRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    session_id = request.session_id or str(uuid.uuid4())
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = handle_appointment(messages)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=traceback.format_exc())

    last_message = request.messages[-1]
    await run_in_threadpool(storage.record_turn, "appointment", session_id, last_message.role, last_message.content)
    await run_in_threadpool(storage.record_turn, "appointment", session_id, "assistant", reply)

    return AppointmentResponse(reply=reply, session_id=session_id)
