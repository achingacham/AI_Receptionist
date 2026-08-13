# AI Receptionist

An AI-powered receptionist chatbot built with FastAPI and Groq.

## Prerequisites

- Python 3.11+
- pip
- Optional: Docker and Docker Compose
- A valid `.env` file with API keys and business details

## Quick start without Docker

1. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   ```

2. **Activate the virtual environment**
   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # or create .env manually
   ```
   Then fill in required values, especially:
   - `GROQ_API_KEY`
   - `BUSINESS_NAME`
   - `BUSINESS_PHONE`
   - `BUSINESS_EMAIL`
   - `BUSINESS_ADDRESS`
   - `RECEPTIONIST_NAME`
   - Optional voice and calendar keys for Twilio/Plivo/Exotel/Cal.com/Sarvam

5. **Run the server**
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```

6. **Verify it is running**
   ```bash
   curl http://localhost:8000/health
   ```

7. Open http://localhost:8000 in your browser.

### Restart helper for local non-Docker deployment

A restart script is included at [restart_service.sh](restart_service.sh):

```bash
chmod +x restart_service.sh
./restart_service.sh
```

This script activates `.venv`, restarts the app, and verifies the health endpoint before exiting.

## Deployment with Docker

### Build the image

```bash
docker build -t ai-receptionist .
```

### Run as a container

```bash
docker run --rm -p 8000:8000 --env-file .env ai-receptionist
```

This starts the FastAPI app on port `8000`.

### Run with Docker Compose

The repository already includes [docker-compose.yml](docker-compose.yml):

```bash
docker compose up --build -d
```

This starts:
- the FastAPI application container
- a Caddy reverse proxy container on ports `80` and `443`

### Docker notes

- The app container reads runtime configuration from `.env`
- Data for SQLite is mounted under `./data`
- Caddy is used for HTTPS/TLS in front of the app when a domain is configured
- For production, set `DOMAIN` in `.env` or environment variables to the public hostname

## Production deployment notes

For a public deployment, you should ensure:

- the server is reachable on a public IP or domain
- HTTPS is enabled via Caddy or a load balancer
- all external API keys are valid
- the `.env` file is not committed to source control
- persistent storage is configured for SQLite and any uploaded/generated data

## Deployment to Azure

This project includes an Azure deployment script for provisioning the required infrastructure.

### Prerequisites

- Azure CLI installed and logged in
- A valid Azure subscription
- Permissions to create resource groups and deploy Bicep templates

### Deploy

```bash
./deploy.sh
```

The script does the following:

1. selects the configured Azure subscription
2. creates the resource group
3. validates the Bicep template in [infra/main.bicep](infra/main.bicep)
4. runs a what-if preview
5. creates the deployment with the parameters in [infra/main.bicepparam](infra/main.bicepparam)

This deploys the app into Azure using the infrastructure defined under [infra/](infra/).

### Azure notes

- The app is designed to run in a containerized environment on Azure
- Secrets are expected to be supplied through environment variables or Azure Key Vault configuration
- Public access is usually exposed using a domain + TLS termination or the Azure Front Door / ingress layer configured in your environment

## Deployment to a plain Linux VM

Use this path when you have a VM with a public IP and want to run the app directly using Docker and Caddy.

### Prerequisites

- Ubuntu or another Linux VM
- SSH access to the VM
- a public IP or domain pointed at the VM
- Docker installed on the machine

### Deploy

Run the script on the VM from the repository root:

```bash
./deploy-vm.sh
```

This script:

1. installs Docker if it is missing
2. opens port `80` and `443` in the OS firewall
3. ensures `.env` exists
4. creates the SQLite persistence directory
5. builds and starts the app using `docker compose up -d --build`
6. checks the health endpoint at `http://localhost/health`

### VM notes

- open inbound traffic on `80` and `443` in your cloud firewall / security group as well as the VM firewall
- set `DOMAIN` in `.env` to your public hostname to enable automatic HTTPS via Caddy
- the app expects a real domain for external voice integrations and secure web traffic

## Project Structure

```
ai-receptionist/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app entry point
│       ├── config.py        # Settings from .env
│       ├── receptionist.py  # AI logic & system prompt
│       └── routes/
│           └── chat.py      # POST /api/chat endpoint
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Caddyfile
├── restart_service.sh
├── README.md
└── data/
```

## Configuration

Edit `.env` to customize the receptionist:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |
| `GROQ_MODEL` | LLM model to use |
| `GROQ_API_URL` | Groq API base URL |
| `BUSINESS_NAME` | Name of the business |
| `BUSINESS_HOURS` | Operating hours |
| `BUSINESS_PHONE` | Contact phone |
| `BUSINESS_EMAIL` | Contact email |
| `BUSINESS_ADDRESS` | Physical address |
| `RECEPTIONIST_NAME` | The receptionist's name |
| `SARVAM_API_KEY` | Used for voice transcription/synthesis |
| `VOICE_PROVIDER` | `plivo`, `twilio`, or `exotel` |
| `CALCOM_API_KEY` | Booking integration key |
| `CALCOM_USERNAME` | Cal.com username |
| `CALCOM_EVENT_TYPE_ID` | Cal.com event type ID |

## API

- `POST /api/chat` — Send messages, receive AI replies
- `POST /api/appointment` — Appointment booking / rescheduling / cancellation flow
- `GET /health` — Health check
- Voice endpoints are exposed for telephony integrations such as Plivo, Twilio, and Exotel

## License

This project is provided as-is for local development and deployment. See repository policies for any additional licensing or deployment restrictions.