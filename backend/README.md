# Backend — DishHome AI Core

FastAPI service that orchestrates the AI call flow: STT → LLM (with tools) → TTS, plus integrations with billing/CRM, OSS, ticketing, and SMS.

This is the **scaffold** — endpoints are stubs.

## Run locally

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # fill values
uvicorn app.main:app --reload
```

Hit `http://localhost:8000/health` — expect `{"status":"ok"}`.

OpenAPI docs at `http://localhost:8000/docs`.

## Layout

```
app/
├── main.py           FastAPI app, CORS, router wiring
├── config.py         pydantic-settings reading .env
└── routers/
    ├── health.py     /health
    └── calls.py      /calls/session, /calls/audio (WebSocket stub)
```

## Next steps (not in this commit)

- Wire AudioSocket bridge from FreeSWITCH on a TCP port.
- Plug streaming faster-whisper STT.
- Plug Ollama client + LangGraph workflow.
- Plug Piper TTS streaming.
- Implement ISP tool calls.
