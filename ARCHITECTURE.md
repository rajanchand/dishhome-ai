# Architecture — DishHome AI Call Center

Industry-grade, production-oriented design for an AI-powered ISP call center serving Dish Media Network (DishHome). Bilingual Nepali/English, integrated with billing/CRM/OSS, with seamless escalation to human agents.

## Core architecture (production grade)

- **Telephony layer:** FreeSWITCH (or Asterisk) with ARI / AudioSocket for real-time bidirectional audio streaming. Industry-standard for carrier-grade call centers.
- **AI core:** Ollama running a fine-tuned Llama 3.1 or Qwen 2.5 model optimized for Nepali + English telecom domain.
- **STT:** Faster-Whisper or Whisper-large-v3 (handles Nepali accents well). Local for privacy and latency.
- **TTS:** Piper TTS or Coqui TTS with a professional DishHome-branded voice — warm, confident, polite.
- **Orchestration:** Python service using LangGraph (or equivalent) for conversation state, tool calling, and workflow.

**Real-time flow:** SIP call → FreeSWITCH → AudioSocket → STT → LLM (with tools) → TTS → back to caller. Latency target: **under 800 ms** per turn.

## Industry-grade features for ISP

- **Customer identification:** Accept Customer ID, mobile number, or Smartcard number. Auto-fetch from billing / CRM via secure API.
- **Smart diagnosis:** For "router offline" — check ONT/ONU status, signal levels, recent outages, PPPoE session, last reboot time. Queries the network monitoring system via tools.
- **Automated actions:**
  - Create ticket in the existing system
  - Auto-assign to correct field team based on location / pincode
  - Give accurate ETA
  - Send SMS confirmation
  - Schedule callback if needed
- **Fallback to human:** Warm transfer to a live agent with full conversation summary attached.
- **Bilingual:** Handles Nepali and English naturally.

## Portal design (DishHome style)

Clean, modern, blue + orange accents, simple navigation, Nepali-friendly. Three personas, three panels.

### 1. Agent / user panel (simple & fast)

- Live call queue
- Active AI conversations with live transcript
- One-click takeover of any call
- Customer 360° view (account, billing, devices, tickets)
- Minimalist — agents should use it without thinking

### 2. Supervisor panel

- Live monitoring of AI + human agents
- AI performance metrics (resolution rate, average handle time, escalation rate)
- Jump into any call
- Change AI voice / model on the fly
- Manage workflows and prompts

### 3. Super admin panel (powerful but clean)

- Full AI training interface (upload call recordings, add FAQs, RAG knowledge base)
- Model management (switch Ollama models)
- Voice management (upload new voice samples)
- Analytics + call recording search
- User & role management
- System health monitoring
- Integration settings (billing, SMS gateway, field team app)

## Integration requirements

- Connect toll-free 16600122000 and other lines via SIP trunk
- Existing billing system + ticketing system (Freeside fits ISPs well, if open to it)
- SMS gateway for ticket updates
- Real-time network status API
- Call recording storage with searchable index (compliant retention)

## Tech stack

| Layer        | Choice                              |
| ------------ | ----------------------------------- |
| Backend      | Python + FastAPI                    |
| Frontend     | React + TypeScript + Tailwind       |
| Database     | PostgreSQL                          |
| Telephony    | FreeSWITCH                          |
| Queue / state| Redis                               |
| LLM runtime  | Ollama                              |
| Deploy       | Docker + Kubernetes (for scale)     |

Brand colors: DishHome deep blue `#003a70`, accent orange `#f7941d`.

## Where to go next

- [docs/telephony-architecture.md](docs/telephony-architecture.md) — real-time AI integration deep dive
- [docs/roadmap.md](docs/roadmap.md) — phased delivery plan with milestones
