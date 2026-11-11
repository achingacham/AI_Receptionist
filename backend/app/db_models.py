from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Call(Base):
    """A chat session, appointment session, or voice call."""

    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(
        String(20), index=True
    )  # chat, appointment, plivo, twilio, exotel, daily
    external_id: Mapped[str] = mapped_column(
        String(128), index=True
    )  # session_id, call_sid, stream_id, room name
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="call", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    call: Mapped["Call"] = relationship(back_populates="messages")


class CallerMessage(Base):
    """A structured inquiry record captured when an inquiry falls outside the Knowledge Base."""

    __tablename__ = "caller_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    caller_name: Mapped[str] = mapped_column(String(100))
    caller_phone: Mapped[str] = mapped_column(String(50))
    inquiry_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, resolved, archived
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
