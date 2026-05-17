# DishHome AI Call Center

AI-powered ISP call center system for Dish Media Network (DishHome). Carrier-grade telephony (FreeSWITCH) + real-time streaming AI (STT / LLM / TTS) + bilingual Nepali/English agent that handles router diagnostics, ticket creation, field-team dispatch, and seamless human handoff.

## Status

Working portal + FastAPI backend. The app includes auth, admin/user management,
live-call views, inbox, contacts, FAQs, campaign flows, voice lab, Huawei/OSS
mock diagnostics, metrics, and Twilio/ElevenLabs integration surfaces.

Telephony, STT, LLM, and TTS are still integration-stage: the interfaces and
demo flows exist, but production SIP/media, streaming STT, LangGraph tooling,
and branded TTS need to be wired before real customer traffic.

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
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
# http://localhost:8000/health -> {"status":"ok"}
```

### Frontend

```sh
cd frontend
npm install
npm run dev
# http://127.0.0.1:3000
```

Demo login: `admin` / `dishhome123`.

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
