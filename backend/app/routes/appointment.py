from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..appointment_handler import handle_appointment

router = APIRouter(prefix="/api", tags=["appointment"])


class Message(BaseModel):
    role: str
    content: str


class AppointmentRequest(BaseModel):
    messages: list[Message]


class AppointmentResponse(BaseModel):
    reply: str


@router.post("/appointment", response_model=AppointmentResponse)
async def appointment_endpoint(request: AppointmentRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        reply = handle_appointment(messages)
        return AppointmentResponse(reply=reply)
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=traceback.format_exc())
