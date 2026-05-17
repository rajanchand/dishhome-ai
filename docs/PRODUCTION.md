# Production Deployment Runbook

This project can be deployed as two long-running services:

- FastAPI backend on `:8000`
- Static React frontend served by nginx on `:80`

Real telephony, STT, LLM, and TTS provider credentials are operational choices;
do not hardcode them or commit `.env`.

## Required Environment

Set these before starting production:

```sh
APP_ENV=production
APP_SECRET_KEY=<64+ chars from: python -c 'import secrets; print(secrets.token_urlsafe(64))'>
PUBLIC_BASE_URL=https://api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
POSTGRES_PASSWORD=<strong password>
DATABASE_URL=postgresql://dishhome:<strong password>@postgres:5432/dishhome_ai
VITE_API_BASE=https://api.example.com
TWILIO_VALIDATE_SIGNATURES=true
```

Optional but expected for real operations:

```sh
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
ELEVENLABS_API_KEY=
OLLAMA_HOST=
OLLAMA_MODEL=
ENABLE_AUDIO_SERVER=true
```

## Docker Compose Production

```sh
cp .env.example .env
# edit .env with production values above
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml ps
```

Health checks:

```sh
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
curl -fsS http://127.0.0.1/healthz
```

## Before Real Traffic

1. Put TLS in front of both services with nginx, Caddy, a cloud load balancer,
   or Vercel/managed hosting.
2. Pin `CORS_ALLOWED_ORIGINS` to the exact frontend origin.
3. Confirm `PUBLIC_BASE_URL` is the exact HTTPS URL Twilio will call.
4. Keep `TWILIO_VALIDATE_SIGNATURES=true`.
5. Apply database migrations and verify `/health/ready`.
6. Create non-demo users, rotate the seeded demo passwords, and revoke old
   sessions from `/admin/login-activity`.
7. Configure backup/restore for Postgres.
8. Export logs and metrics to your monitoring stack.

## Deployment Gates

Every deployment should pass:

```sh
cd frontend && npm ci && npm run build
python3.13 -m py_compile $(rg --files backend/app -g '*.py')
docker compose -f docker-compose.yml config
docker compose -f docker-compose.prod.yml config
```

GitHub Actions runs the equivalent checks on every push to `main` and every PR.

## Known Non-Production Work Still Required

- Replace mock ISP integration data with real billing/OSS/ticketing adapters.
- Persist telephony call sessions in Redis or Postgres instead of process memory.
- Wire FreeSWITCH AudioSocket to the backend audio server.
- Add VAD, streaming STT, LangGraph tool workflow, and production TTS.
- Add end-to-end browser tests for the protected portal flows.
