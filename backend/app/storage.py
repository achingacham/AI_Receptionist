"""Thin helper functions for logging calls/conversations to SQLite.

All functions are sync (SQLAlchemy has no async SQLite driver worth using at
this scale) — call them via `starlette.concurrency.run_in_threadpool` from
async route handlers/event handlers so the event loop isn't blocked.
"""

from datetime import datetime, timezone

from .db import SessionLocal
from .db_models import Call, Message


def get_or_create_call(channel: str, external_id: str) -> int:
    with SessionLocal() as session:
        call = session.query(Call).filter_by(channel=channel, external_id=external_id).first()
        if call is None:
            call = Call(channel=channel, external_id=external_id)
            session.add(call)
            session.commit()
            session.refresh(call)
        return call.id


def start_call(channel: str, external_id: str) -> int:
    return get_or_create_call(channel, external_id)


def end_call(call_id: int) -> None:
    with SessionLocal() as session:
        call = session.get(Call, call_id)
        if call is not None:
            call.ended_at = datetime.now(timezone.utc)
            session.commit()


def log_message(call_id: int, role: str, content: str) -> None:
    with SessionLocal() as session:
        session.add(Message(call_id=call_id, role=role, content=content))
        session.commit()


def record_turn(channel: str, external_id: str, role: str, content: str) -> None:
    """Get-or-create the session, then append one message to it."""
    call_id = get_or_create_call(channel, external_id)
    log_message(call_id, role, content)


def _flatten_content(content) -> str:
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                parts.append(str(part.get("text", part)))
            else:
                parts.append(str(part))
        return " ".join(parts)
    return str(content)


def log_transcript(call_id: int, messages: list[dict]) -> None:
    """Bulk-insert a full transcript, skipping the system prompt.

    Used for voice calls, where the full turn-by-turn history is only
    available once the call ends (via the pipeline's LLMContext).
    """
    with SessionLocal() as session:
        for m in messages:
            role = m.get("role")
            if role == "system":
                continue
            session.add(Message(call_id=call_id, role=role, content=_flatten_content(m.get("content"))))
        session.commit()
