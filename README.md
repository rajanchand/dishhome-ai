# DishHome AI Call Center

AI-powered ISP call center system for Dish Media Network (DishHome). Carrier-grade telephony (FreeSWITCH) + real-time streaming AI (STT / LLM / TTS) + bilingual Nepali/English agent that handles router diagnostics, ticket creation, field-team dispatch, and seamless human handoff.

## Status

Early scaffold. The architecture is fully designed; runnable services are stubs that boot and pass health checks.

## Repository layout

```
.
├── ARCHITECTURE.md        Full system blueprint
├── docs/
│   ├── telephony-architecture.md   Real-time AI integration deep dive
│   └── roadmap.md                  Phased delivery plan
├── backend/               FastAPI AI core service (Python)
├── frontend/              React + Vite + Tailwind agent panel
├── telephony/             FreeSWITCH configs (placeholder)
├── docker-compose.yml     Local stack: postgres, redis, backend, frontend
├── .env.example           Required environment variables
└── .gitignore
```

## Quick start

### Backend

```sh
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# http://localhost:8000/health -> {"status":"ok"}
```

### Frontend

```sh
cd frontend
npm install
npm run dev
# Open the URL Vite prints
```

### Full stack (Docker)

```sh
cp .env.example .env       # edit values
docker compose up --build
```

## Tech stack

- Telephony: FreeSWITCH (SIP trunk + AudioSocket media bridge)
- STT: faster-whisper (large-v3)
- LLM: Ollama, fine-tuned Llama 3.1 / Qwen 2.5 (Nepali + English telecom domain)
- TTS: Piper TTS with a DishHome-branded voice
- Orchestration: Python + FastAPI + LangGraph
- Frontend: React + Vite + TypeScript + Tailwind
- Data: PostgreSQL, Redis
- Deploy: Docker, Kubernetes

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and [docs/telephony-architecture.md](docs/telephony-architecture.md) for the real-time integration.

## License

TBD.
