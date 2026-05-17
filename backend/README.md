# Backend — DishHome AI Core

FastAPI service that orchestrates the AI call flow: STT → LLM (with tools) → TTS, plus integrations with billing/CRM, OSS, ticketing, and SMS.

This is still a scaffold for real telephony/AI, but many product endpoints are
now live against Postgres-backed or mock-backed data: auth, calls, metrics,
admin, Huawei diagnostics, inbox, contacts, FAQs, campaigns, voice lab, and
telephony control surfaces.

## Run locally

```sh
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill values
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Hit `http://localhost:8000/health` — expect `{"status":"ok"}`.

OpenAPI docs at `http://localhost:8000/docs`.

## Layout

```
app/
├── main.py           FastAPI app, CORS, lifespan, router wiring
├── config.py         pydantic-settings reading .env
├── database.py       SQLAlchemy async engine/session setup
├── audio_server.py   AudioSocket TCP server scaffold
├── models/           SQLAlchemy models
└── routers/          auth, calls, admin, integrations, voice, campaigns, etc.
```

## Next steps (not in this commit)

- Wire real FreeSWITCH dialplan to the AudioSocket TCP server.
- Plug streaming faster-whisper STT.
- Plug Ollama client + LangGraph workflow.
- Plug Piper TTS streaming.
- Implement ISP tool calls.
