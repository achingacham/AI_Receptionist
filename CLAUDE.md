# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (from repo root)
uvicorn backend.app.main:app --reload

# Access the app
# http://localhost:8000
```

## Configuration

All runtime settings are loaded from `.env` via `pydantic-settings`. Copy `.env.example` to `.env` and fill in values:

- `LLM_API_KEY` — key for the chat completions provider, e.g. [console.groq.com](https://console.groq.com) or Azure OpenAI. **This is the primary AI key, not Anthropic.**
- `LLM_MODEL` — model or deployment name (e.g. `mixtral-8x7b-32768`)
- `LLM_API_URL` — base URL of any OpenAI-compatible chat completions endpoint (default `https://api.groq.com/openai/v1`; Azure OpenAI's unified `https://<resource>.openai.azure.com/openai/v1` also works)
- `SARVAM_API_KEY` — required for voice calls (STT + TTS via Sarvam AI)
- `CALCOM_API_KEY`, `CALCOM_EVENT_TYPE_ID`, `CALCOM_USERNAME` — Cal.com scheduling integration
- `PLIVO_*` / `TWILIO_*` — telephony provider credentials (`VOICE_PROVIDER=plivo` or `twilio`)
- Business identity: `BUSINESS_NAME`, `BUSINESS_HOURS`, `BUSINESS_PHONE`, `BUSINESS_EMAIL`, `BUSINESS_ADDRESS`, `RECEPTIONIST_NAME`

## Architecture

The system has three interaction modes that share a common LLM client and scenario prompt system:

**1. Text chat** (`POST /api/chat`)
`routes/chat.py` → `receptionist.chat()` → `LLMClient.generate()`

**2. Appointment booking** (`POST /api/appointment`)
`routes/appointment.py` → `appointment_handler.handle_appointment()` — runs a two-pass LLM pipeline: first extracts structured intent JSON from the conversation, then executes the Cal.com API action (book/reschedule/cancel/check_availability), and finally passes calendar results back to the LLM for a natural-language reply.

**3. Voice calls** (WebSocket endpoints `/plivo/ws` and `/twilio/ws`)
`routes/voice.py` / `routes/voice_twilio.py` → `voice/pipeline.py` — builds a real-time [Pipecat](https://github.com/pipecat-ai/pipecat) pipeline: `Sarvam STT → OpenAI-compatible LLM → Sarvam TTS`. Plivo and Twilio bots share the same pipeline via `build_pipeline()`.

### Key modules

| File | Purpose |
|---|---|
| `backend/app/config.py` | Single source of truth for all settings |
| `backend/app/llm_client.py` | HTTP wrapper around any OpenAI-compatible chat completions API |
| `backend/app/receptionist.py` | Builds the system prompt from scenario templates and settings |
| `backend/app/scenarios/` | Prompt templates keyed by scenario name (`general`, `appointment`, `trial_followup`, `clinic_reschedule`, `feedback_call`, `appointment_confirmation`) |
| `backend/app/cal_com_client.py` | Cal.com v2 REST client (slots, book, reschedule, cancel) |
| `backend/app/voice/pipeline.py` | Transport-agnostic Pipecat pipeline shared by Plivo and Twilio |
| `frontend/app.js` | Chat UI + WebRTC voice call client (Daily.co) |

### Adding a new scenario

1. Create `backend/app/scenarios/my_scenario.py` with a `MY_SCENARIO_PROMPT` string (use `{name}`, `{business}`, `{hours}`, `{phone}`, `{email}`, `{address}` placeholders).
2. Register it in `backend/app/scenarios/__init__.py` under `SCENARIO_PROMPTS`.
3. Pass `"scenario": "my_scenario"` in the `/api/chat` request body.

## Deployment

Azure infrastructure is defined in `infra/main.bicep`. Deploy with:

```powershell
.\deploy.ps1
```

The app runs as a Docker container in Azure Container Apps. Secrets are stored in Azure Key Vault.
