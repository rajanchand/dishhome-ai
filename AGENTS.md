# AGENTS.md — Session continuity for AI agents

If you're an AI agent (Claude Code, Cursor, etc.) picking up this project — read this first. It explains what's built, what's mocked, how to run things, and where to take the project next.

## Project

**Dish Media Network (DishHome) AI Call Center.** Carrier-grade telephony (FreeSWITCH) + real-time streaming AI (STT → LLM → TTS) + ISP integrations (billing, OSS, ticketing, SMS) + multi-role portal (agent, supervisor, super admin). Bilingual Nepali/English. Toll-free 16600122000.

Repo: https://github.com/rajanchand/dishhome-ai.git

## Current state (snapshot)

Working scaffold + functional portal with mocked data. All endpoints return real shapes; nothing is hardcoded in the UI. **No real telephony, STT, LLM, or TTS yet** — those live behind stub interfaces.

| Layer | Status |
| --- | --- |
| Architecture docs | ✅ `ARCHITECTURE.md`, `docs/telephony-architecture.md`, `docs/roadmap.md` |
| FastAPI backend | ✅ auth, calls, voice, integrations routers; all data mocked in `app/mock_data.py` |
| React portal | ✅ login + 6 pages (Dashboard, Calls, Call Detail, Voice Lab, Integrations, Settings) |
| Auth | ✅ mock bearer token, in-memory sessions, 3 demo users |
| Voice preview | ✅ Web Speech API demo (real Piper TTS not wired) |
| FreeSWITCH | ❌ placeholder folder only |
| STT / LLM / TTS | ❌ stub interfaces; no real audio yet |
| Real DB | ❌ in-memory dicts/lists |
| Docker | ✅ `docker-compose.yml` (postgres + redis + backend + frontend) |
| CI | ❌ not set up |

## How to run

### Backend (Python 3.13 — NOT 3.14)

`pydantic-core` 2.23.4 has no wheels for Python 3.14 yet. Use 3.13.

```sh
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

OpenAPI: http://127.0.0.1:8000/docs

### Frontend

```sh
cd frontend
npm install
npm run dev   # http://127.0.0.1:5173
```

### Demo login

| Username | Password | Role |
| --- | --- | --- |
| `admin` | `dishhome123` | super_admin |
| `supervisor` | `dishhome123` | supervisor |
| `agent` | `dishhome123` | agent |

Token persists in `localStorage` under key `dh_token`.

### Sample data for testing the portal

- Customer IDs: `DH100234` (active), `DH100997` (overdue, outage), `DH101452` (active)
- Mobile numbers: `9841234567`, `9802112233`, `9818776655`
- Smartcards: `SC-4429981`, `SC-4429120`, `SC-4430018`
- ONT IDs: `ONT-KTM-882441`, `ONT-PKR-110028` (offline), `ONT-ITH-330091`

## Architecture conventions

- **Backend** lives in `backend/app/`. Each router is one file under `routers/`. Mock data is centralized in `mock_data.py` — when wiring real integrations, replace function bodies in `routers/integrations.py` and remove the mock dicts.
- **Frontend** is React 18 + Vite + TypeScript + Tailwind. Brand palette in `tailwind.config.js`: `dishhome-blue` (`#003a70`), `dishhome-orange` (`#f7941d`).
- API client lives at `frontend/src/lib/api.ts`. All requests go through `api.get` / `api.post`, which attach the bearer token automatically. Types for all responses live in the same file.
- Auth state at `frontend/src/lib/auth.tsx` (`AuthProvider`, `useAuth`).
- Routing in `frontend/src/App.tsx` (BrowserRouter + protected `<Layout>` shell).
- Shared UI primitives in `frontend/src/components/ui.tsx`: `PageHeader`, `PageBody`, `Card`, `StatCard`, `Button`, `Badge`, `Input`, `statusTone`.

## File map

```
backend/
├── app/
│   ├── main.py              FastAPI app + CORS + router wiring
│   ├── config.py            pydantic-settings
│   ├── mock_data.py         CUSTOMERS, CALLS, TICKETS, ONT_STATUS, VOICES, USERS
│   └── routers/
│       ├── health.py        GET /health
│       ├── auth.py          POST /auth/login, GET /auth/me, POST /auth/logout
│       ├── calls.py         GET /calls, /calls/stats, /calls/{id}; POST /calls/session; WS /calls/audio/{id}
│       ├── voice.py         GET /voice/voices, POST /voice/preview
│       └── integrations.py  /integrations/dishhome/customer/{q}, /router-status/{ont}, /router-reboot/{ont}, /ticket, /tickets, /test
├── requirements.txt
└── Dockerfile

frontend/src/
├── App.tsx                  Router + RequireAuth
├── main.tsx                 Entry
├── index.css                Tailwind directives
├── vite-env.d.ts            Vite env types
├── lib/
│   ├── api.ts               fetch wrapper + types + token helpers
│   └── auth.tsx             AuthContext / AuthProvider / useAuth
├── components/
│   ├── Layout.tsx           Sidebar + Outlet
│   └── ui.tsx               Shared primitives
└── pages/
    ├── Login.tsx
    ├── Dashboard.tsx
    ├── Calls.tsx
    ├── CallDetail.tsx
    ├── VoiceLab.tsx
    ├── Integrations.tsx
    └── Settings.tsx
```

## Where to take it next (priority order)

### Phase 2 — Real streaming AI core

1. **FreeSWITCH** — write dialplan that routes inbound calls on the test DID to an extension that opens an AudioSocket TCP connection to backend port `${FREESWITCH_AUDIOSOCKET_PORT}` (default `4000`).
2. **Backend audio server** — new module `backend/app/audio_server.py`. asyncio TCP server that reads 20ms PCM frames per call session.
3. **VAD** — wire `silero-vad` to detect end-of-utterance.
4. **STT** — wire `faster-whisper` (large-v3) with streaming partial transcripts.
5. **LLM** — Ollama client; build LangGraph workflow with tool calls hitting the existing `/integrations/dishhome/*` endpoints.
6. **TTS** — wire Piper with custom DishHome voice; stream audio chunks back via AudioSocket.

### Phase 3 — Production-grade things

- Replace `mock_data.py` with real Postgres tables + asyncpg queries.
- Real auth: OAuth2 with PKCE or JWT signed with RS256. Drop the in-memory `_SESSIONS` dict in `routers/auth.py`.
- Add CI: GitHub Actions running `ruff`, `pytest`, `tsc --noEmit`, `npm run build`.
- Containerize FreeSWITCH and add to `docker-compose.yml`.
- Monitoring: Prometheus exporters in backend + Grafana dashboard for latency/resolution rate.
- Call recording storage (S3-compatible bucket) + searchable transcript index.

### Smaller polish wins

- Replace dummy nav icons (`▦ ☏ ♪ ⚙ ⚒`) with `lucide-react` icons.
- Add toast notifications instead of `alert()` in `Integrations.tsx`.
- Real-time call updates via WebSocket — push new transcript turns into `CallDetail.tsx`.
- Live "monitor" mode on Calls page (auto-refresh every 5s).
- Internationalization (Nepali UI strings) — i18next.

## Gotchas / known issues

- **Python 3.14 doesn't work** for the current `requirements.txt`. Use 3.13. If you want to bump: pin pydantic to >=2.10 (which has 3.14 wheels) — confirm before changing.
- **CORS** is wide-open (`*` methods/headers) but origins are limited to `http://localhost:5173`. Production: tighten and use mTLS for service-to-service.
- **`alert()`** used in Integrations actions. Fine for the scaffold; replace before any real user touches it.
- **Vite serves with `--host 0.0.0.0`** in `package.json` — anyone on your LAN can hit the dev server. Tighten to `127.0.0.1` for dev if you don't want that.
- **Mock auth sessions are in-memory** — they vanish when uvicorn reloads. Re-login after any backend code edit.

## Style preferences observed from the user

- Wants industry / enterprise-grade design, not a toy demo.
- Inspired by [tingting.io](https://www.tingting.io) (Nepali AI call center). Aim for that polish.
- Nepali + English bilingual everywhere customer-facing.
- DishHome brand colors: deep blue `#003a70`, accent orange `#f7941d`.
- Commits should attribute Claude as co-author.
- User's email for commits (local config): `rajanchand48@gmail.com`.

## Verification commands (use these before claiming "it works")

```sh
# Backend
curl http://127.0.0.1:8000/health                              # {"status":"ok"}
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'content-type: application/json' \
  -d '{"username":"admin","password":"dishhome123"}' | jq -r .token)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/calls/stats

# Frontend
curl -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5173/
cd frontend && npx tsc --noEmit         # must be silent
```

## Things to ASK the user before doing

- Wiring a real LLM provider key or SIP trunk credentials — these are operational decisions.
- Replacing the mock auth with a real identity provider — needs to know which one (OAuth provider, Active Directory, etc.).
- Anything that touches GitHub PR/merge state — confirm first.
- Pinning new dependency versions — list the change, get sign-off.

## Things you CAN do without asking

- Add UI pages, components, polish.
- Add backend endpoints that read from `mock_data.py`.
- Refactor for clarity if behavior is preserved.
- Fix bugs you find while working on something else.
- Add tests.
