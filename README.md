# AI Receptionist

An AI-powered receptionist chatbot built with FastAPI and Groq.

## Setup

1. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment**
   ```bash
   # Windows (bash/Git Bash)
   source venv/Scripts/activate

   # Windows (cmd)
   venv\Scripts\activate.bat

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and set your GROQ_API_KEY and business details
   ```

5. **Run the server**
   ```bash
   uvicorn backend.app.main:app --reload
   ```

6. Open http://localhost:8000 in your browser.

## Project Structure

```
ai-receptionist/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app entry point
│       ├── config.py        # Settings from .env
│       ├── receptionist.py  # Claude AI logic & system prompt
│       └── routes/
│           └── chat.py      # POST /api/chat endpoint
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── .env.example
├── requirements.txt
└── README.md
```

## Configuration

Edit `.env` to customize the receptionist:

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |
| `BUSINESS_NAME` | Name of the business |
| `BUSINESS_HOURS` | Operating hours |
| `BUSINESS_PHONE` | Contact phone |
| `BUSINESS_EMAIL` | Contact email |
| `BUSINESS_ADDRESS` | Physical address |
| `RECEPTIONIST_NAME` | The receptionist's name (default: Alex) |

## API

- `POST /api/chat` — Send messages, receive AI replies
- `GET /health` — Health check