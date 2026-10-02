# AGENTS.md

Guidance for AI coding agents (Claude Code, GitHub Copilot, Gemini CLI, Codex, Cursor, etc.) working in this repository. This is the single source of truth — tool-specific files (`CLAUDE.md`, `.gemini/settings.json`, `.github/agents/*.agent.md`) only point here.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (from repo root)
uvicorn backend.app.main:app --reload

# Access the app
# http://localhost:8000

# Tests and lint
pytest -q
ruff check --fix . && ruff format .
pre-commit run --all-files
```

## Configuration

All runtime settings are loaded from `.env` via `pydantic-settings` (`backend/app/config.py`). Copy `.env.example` to `.env` and fill in values:

- `LLM_API_KEY` — key for the chat completions provider, e.g. [console.groq.com](https://console.groq.com) or Azure OpenAI. **This is the primary AI key, not Anthropic.**
- `LLM_MODEL` — model or deployment name (e.g. `mixtral-8x7b-32768`)
- `LLM_API_URL` — base URL of any OpenAI-compatible chat completions endpoint (default `https://api.groq.com/openai/v1`; Azure OpenAI's unified `https://<resource>.openai.azure.com/openai/v1` also works)
- `SARVAM_API_KEY` — required for voice calls (STT + TTS via Sarvam AI)
- `CALCOM_API_KEY`, `CALCOM_EVENT_TYPE_ID`, `CALCOM_USERNAME` — Cal.com scheduling integration
- `PLIVO_*` / `TWILIO_*` / `EXOTEL_*` — telephony provider credentials (`VOICE_PROVIDER=plivo`, `twilio`, or `exotel`)
- Business identity: `BUSINESS_NAME`, `BUSINESS_HOURS`, `BUSINESS_PHONE`, `BUSINESS_EMAIL`, `BUSINESS_ADDRESS`, `RECEPTIONIST_NAME`

## Architecture

The system has three interaction modes that share a common LLM client and scenario prompt system:

**1. Text chat** (`POST /api/chat`)
`routes/chat.py` → `receptionist.chat()` → `LLMClient.generate()`

**2. Appointment booking** (`POST /api/appointment`)
`routes/appointment.py` → `appointment_handler.handle_appointment()` — runs a two-pass LLM pipeline: first extracts structured intent JSON from the conversation, then executes the Cal.com API action (book/reschedule/cancel/check_availability), and finally passes calendar results back to the LLM for a natural-language reply.

**3. Voice calls**
A real-time [Pipecat](https://github.com/pipecat-ai/pipecat) pipeline: `Sarvam STT → OpenAI-compatible LLM → Sarvam TTS`, built by `build_pipeline()` in `voice/pipeline.py` and shared by all providers.

| Provider | Webhook / WebSocket | Route | Bot |
|---|---|---|---|
| Generic (dispatches on `VOICE_PROVIDER`; Plivo default) | `POST /call/incoming`, WS `/call/stream` | `routes/voice.py` | `voice/plivo_bot.py` / `twilio_bot.py` / `exotel_bot.py` |
| Twilio | `POST /twilio/incoming`, WS `/twilio/stream` | `routes/voice_twilio.py` | `voice/twilio_bot.py` |
| Exotel | `POST /exotel/incoming`, WS `/exotel/stream` | `routes/voice_exotel.py` | `voice/exotel_bot.py` (see [EXOTEL_SETUP.md](EXOTEL_SETUP.md)) |
| Browser (Daily WebRTC) | `POST /api/voice/start` | `routes/voice_daily.py` | `voice/daily_bot.py` |
| Browser test (no telephony) | `POST /sarvam/voice-chat` | `routes/sarvam_test.py` | — |

### Key modules

| File | Purpose |
|---|---|
| `backend/app/config.py` | Single source of truth for all settings |
| `backend/app/llm_client.py` | HTTP wrapper around any OpenAI-compatible chat completions API |
| `backend/app/receptionist.py` | Builds the system prompt from scenario templates and settings |
| `backend/app/scenarios/` | Prompt templates keyed by scenario name (`general`, `appointment`, `trial_followup`, `clinic_reschedule`, `feedback_call`, `appointment_confirmation`) |
| `backend/app/cal_com_client.py` | Cal.com v2 REST client (slots, book, reschedule, cancel) |
| `backend/app/voice/pipeline.py` | Transport-agnostic Pipecat pipeline shared by all voice providers |
| `frontend/app.js` | Chat UI + WebRTC voice call client (Daily.co) |

### Adding a new scenario

1. Create `backend/app/scenarios/my_scenario.py` with a `MY_SCENARIO_PROMPT` string (use `{name}`, `{business}`, `{hours}`, `{phone}`, `{email}`, `{address}` placeholders).
2. Register it in `backend/app/scenarios/__init__.py` under `SCENARIO_PROMPTS`.
3. Pass `"scenario": "my_scenario"` in the `/api/chat` request body.

## Working rules

- Preserve the existing architecture and conventions; prefer targeted edits over broad refactors.
- Keep secrets and credentials out of source files — use environment variables via `config.py`.
- Before changing a business-critical flow, trace it end to end: route → handler → provider client.
- For voice and scheduling work, check provider-specific requirements (Plivo/Twilio/Exotel/Daily, Cal.com) before editing.
- Validate with the most relevant local command (targeted test, lint, or server startup).
- When done, summarize what changed, why, how it was verified, and any config changes or follow-up risks.

## Code quality

- Python is linted and formatted with ruff.
- Pre-commit (`.pre-commit-config.yaml`) runs `ruff check --fix`, `ruff format`, and `pytest` on every commit.
- Tests live in `backend/tests/`.

## Deployment

Azure infrastructure is defined in `infra/main.bicep`. Deploy with:

```powershell
.\deploy.ps1
```

The app runs as a Docker container in Azure Container Apps. Secrets are stored in Azure Key Vault. Open infra and deployment tasks are tracked in [TODO.md](TODO.md).
