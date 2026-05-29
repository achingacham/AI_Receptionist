# Exotel Integration Guide

This guide explains how to set up Exotel as your telephony provider for the AI Receptionist.

## Overview

Exotel is a cloud-based telecom platform popular in India. It provides:
- Virtual phone numbers (Indian and international)
- IVR and call handling APIs
- Webhook-based incoming call management
- WebSocket support for real-time audio streaming

The AI Receptionist integrates with Exotel using the same TwiML XML format as Twilio, making it a drop-in replacement.

## Prerequisites

1. **Exotel Account**: Sign up at [www.exotel.com](https://www.exotel.com)
2. **API Credentials**: 
   - SID (Account identifier)
   - Token (API key)
   - Subdomain (your Exotel workspace subdomain)
3. **Phone Number**: Provision a number in your Exotel account (India-based)

## Configuration

### Step 1: Get Your Exotel Credentials

1. Log in to [Exotel Dashboard](https://dashboard.exotel.com)
2. Go to **Settings** → **API** (or **Account** → **API Keys**)
3. Copy your:
   - **SID** (e.g., `exotelclient123`)
   - **Token** (your API authentication key)
   - **Subdomain** (e.g., `mycompany` for `mycompany.exotel.com`)

### Step 2: Update `.env`

Add your Exotel credentials to `.env`:

```env
VOICE_PROVIDER=exotel

EXOTEL_SID=your_exotel_sid
EXOTEL_TOKEN=your_exotel_token
EXOTEL_SUBDOMAIN=your_subdomain
EXOTEL_PHONE_NUMBER=+91xxxxxxxxxx
```

### Step 3: Deploy

Run the deployment script:

```bash
python deploy_agent.py
```

This will:
- Push Exotel secrets to Azure Key Vault
- Update the Container App with new environment variables
- Create new webhook endpoints at `/exotel/incoming`

### Step 4: Configure Exotel Webhook

1. Log in to **Exotel Dashboard**
2. Go to **Phone Numbers** → Select your number
3. Under **Incoming Call Settings**:
   - Set **Receive Incoming Calls** to **API**
   - Set **Webhook URL** to:
     ```
     POST https://<your-app-url>/exotel/incoming
     ```
   - Leave other settings at defaults
4. **Save**

Replace `<your-app-url>` with your Azure Container App URL (e.g., `https://aireceptionistprod7mputf-app.delightfulwave-df7a2549.centralindia.azurecontainerapps.io`)

## How It Works

1. **Incoming Call** → Exotel sends webhook to `/exotel/incoming`
2. **TwiML Response** → App returns XML with WebSocket stream URL
3. **Audio Stream** → Exotel connects to `/exotel/stream` WebSocket
4. **Pipeline** → Sarvam STT → Groq LLM → Sarvam TTS
5. **Response** → Audio sent back to caller via Exotel

## Audio Format

- **Codec**: PCM (linear 16-bit)
- **Sample Rate**: 8 kHz (8000 Hz)
- **Bidirectional**: Yes (caller and AI speak simultaneously)

## Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/exotel/incoming` | POST | Webhook for incoming calls (returns TwiML) |
| `/exotel/stream` | WebSocket | Real-time bidirectional audio stream |

## Advantages of Exotel

- **India-based**: Better local coverage and pricing for Indian numbers
- **No Twilio fees**: Often cheaper than Twilio for India-specific use cases
- **Webhook-based**: Same easy integration pattern
- **Compliant**: Meets Indian telecom regulations

## Troubleshooting

### Call Not Coming Through

1. **Check webhook URL**: Verify it's reachable from Exotel's servers
   ```bash
   curl -X POST https://<your-app-url>/health
   ```
   Should return `{"status": "ok", ...}`

2. **Check logs**: 
   ```bash
   az containerapp logs show --name <app-name> --resource-group <rg-name> --follow
   ```

3. **Verify credentials**: Ensure `EXOTEL_SID` and `EXOTEL_TOKEN` are correct in Key Vault

### Audio Quality Issues

1. **Check Sarvam STT**: Test at `/sarvam/test` endpoint
2. **Check network latency**: Exotel → Azure connection should be < 100ms for India
3. **Monitor logs**: Look for STT/TTS errors in Container App logs

### Switching Between Providers

To switch from Exotel back to Twilio:

```bash
# Update .env
VOICE_PROVIDER=twilio

# Redeploy
python deploy_agent.py --skip-infra --skip-build
```

No code changes needed — the routing logic handles provider switching automatically.

## API Reference

For more details on Exotel's API, see [Exotel API Docs](https://developer.exotel.com/).
