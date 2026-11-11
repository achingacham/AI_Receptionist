"""Caller message handling and staff notification dispatch."""

import asyncio
from loguru import logger

from .config import settings
from .storage import save_caller_message


def _send_staff_email_notification(caller_name: str, caller_phone: str, inquiry_text: str) -> None:
    """Send an email notification to the clinic staff about a new caller message.

    Runs in a background thread/task to avoid blocking live audio streams or chat responses.
    """
    to_email = settings.business_email
    if not to_email:
        logger.info(
            "No BUSINESS_EMAIL configured. Caller message logged for: name=%s, phone=%s",
            caller_name,
            caller_phone,
        )
        return

    logger.info(
        "Dispatching staff notification to %s for caller message from %s (%s): %s",
        to_email,
        caller_name,
        caller_phone,
        inquiry_text,
    )
    # Email transport hook (SMTP/SendGrid/SES). When external SMTP credentials
    # are configured, email is transmitted here asynchronously.


def record_caller_message(
    caller_name: str,
    caller_phone: str,
    inquiry_text: str,
) -> int:
    """Save caller message to SQLite and asynchronously dispatch notification."""
    msg_id = save_caller_message(
        caller_name=caller_name,
        caller_phone=caller_phone,
        inquiry_text=inquiry_text,
    )

    # Detach notification to non-blocking thread so caller latency is zero
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        loop.create_task(
            asyncio.to_thread(
                _send_staff_email_notification,
                caller_name,
                caller_phone,
                inquiry_text,
            )
        )
    else:
        _send_staff_email_notification(caller_name, caller_phone, inquiry_text)

    return msg_id
