# Phased Implementation Roadmap

## Phase 1 — Foundation (4–6 weeks)

- Stand up FreeSWITCH with SIP trunk against a test DID.
- Wire basic AI bridge: greet caller, identify by phone number, transfer to human queue.
- Repo + CI scaffolding, observability baseline (Prometheus + Grafana).

**Done when:** A real call to the test number is greeted by the AI and successfully transferred to a human agent.

## Phase 2 — Streaming AI core (6–8 weeks)

- Streaming STT (faster-whisper) + streaming TTS (Piper) wired through AudioSocket.
- Ollama LLM with LangGraph orchestrator and tool-calling scaffolding.
- First two tools: `get_customer_info`, `create_ticket`.
- Basic conversation memory + bilingual prompt tuning (Nepali + English).

**Done when:** End-to-end turn latency < 1.2 s for a happy-path "create ticket" conversation.

## Phase 3 — ISP integrations + diagnostics (4–6 weeks)

- Billing / CRM connector.
- Network OSS connector — ONT/ONU status, signal, last reboot, outages.
- Ticketing assignment by location, SMS gateway, ETA calculation.
- Bilingual fine-tuning on real call transcripts.

**Done when:** "Router offline" flow resolves remotely or dispatches a field team with SMS confirmation, with no human in the loop on the happy path.

## Phase 4 — Dashboards + supervisor tools + go-live (4–6 weeks)

- Agent panel (live queue, transcript, takeover, customer 360°).
- Supervisor panel (live monitoring, metrics, jump-in, prompt management).
- Super admin panel (model + voice management, RAG ingest, analytics, recordings search).
- Shadow-mode go-live: AI runs in parallel with human agents on a slice of traffic before full cutover.

**Done when:** AI handles >50% of inbound volume end-to-end with resolution rate and CSAT meeting target.

## Hardware (start)

- 2–4 GPU servers (A100 / H100 or RTX 4090) for STT + LLM + TTS.
- Separate reliable hosts for FreeSWITCH.
- PostgreSQL + Redis on managed or HA cluster.

## Risks to track

- SIP trunk quality and codec negotiation — schedule loadtests early.
- Nepali STT accuracy on rural accents — collect transcripts in Phase 2 for fine-tuning.
- Field-team app integration timeline — dependency on external vendor.
- Compliance for call recording retention — confirm with legal before Phase 4 go-live.
