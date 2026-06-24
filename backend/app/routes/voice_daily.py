import asyncio
import httpx
from fastapi import APIRouter, HTTPException
from ..config import settings
from ..voice.daily_bot import run_daily_bot

router = APIRouter(prefix="/api/voice", tags=["voice-browser"])

DAILY_BASE = "https://api.daily.co/v1"

async def _daily_post(path: str, body: dict) -> dict:
    headers = {"Authorization": f"Bearer {settings.daily_api_key}"}
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{DAILY_BASE}{path}", json=body, headers=headers)
        r.raise_for_status()
        return r.json()

@router.post("/start")
async def start_voice_call():
    if not settings.daily_api_key:
        raise HTTPException(503, "DAILY_API_KEY not configured")

    # 1. Create an ephemeral room (auto-deletes after 10 min of no participants)
    room = await _daily_post("/rooms", {
        "properties": {"exp": int(__import__("time").time()) + 600, "eject_at_room_exp": True}
    })
    room_url = room["url"]

    # 2. Create a user token (allows mic access)
    user_token = await _daily_post("/meeting-tokens", {
        "properties": {"room_name": room["name"], "is_owner": False}
    })

    # 3. Create a bot token and start the bot in the background
    bot_token = await _daily_post("/meeting-tokens", {
        "properties": {"room_name": room["name"], "is_owner": True}
    })
    asyncio.create_task(run_daily_bot(room_url, bot_token["token"]))

    return {"room_url": room_url, "token": user_token["token"]}
