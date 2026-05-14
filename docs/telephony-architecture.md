# Telephony + Real-Time AI Integration Architecture

Industry-grade, low-latency, production-ready design tailored for high-volume ISP support in Nepal — bilingual Nepali/English, toll-free numbers (e.g. 16600122000), integration with existing billing/CRM.

## 1. High-level architecture

```
PSTN / SIP Trunk (NTC / Ncell / Provider)
          ↓
   FreeSWITCH  (media + signaling engine)
          ↓  (mod_audiosocket / mod_event_socket)
   Real-time audio streaming (bidirectional raw PCM)
          ↓
   AI Core Service  (Python / FastAPI)
   ├── VAD              (Voice Activity Detection)
   ├── Streaming STT    (faster-whisper)
   ├── Conversation     (LangGraph: state + tools)
   ├── Ollama LLM       (fine-tuned Llama 3.1 / Qwen 2.5)
   └── Streaming TTS    (Piper / Coqui — DishHome voice)
          ↓
   Back to FreeSWITCH → Caller
```

Key principles:

- **Streaming everywhere** — no full-sentence waits.
- **Low latency** — target 600–1200 ms end-to-end turn time.
- **Scalable & resilient** — horizontal scaling, graceful fallback to human agents.
- **Privacy & compliance** — all processing on-prem or in private cloud.

## 2. Telephony layer: FreeSWITCH (recommended)

**Why FreeSWITCH over Asterisk?** FreeSWITCH excels in high concurrency, media handling, and real-time AI integrations. Modular, event-driven, handles thousands of simultaneous calls — fits a national ISP like DishHome.

Core setup:

- **SIP trunk:** Connect existing toll-free and DID numbers via SIP from providers.
- **Dialplan:** Route incoming calls to AI context (e.g. extension `1000` → AI bridge).
- **Media handling:**
  - `mod_audiosocket` (or equivalent media bug) for raw 16-bit PCM streaming over TCP/WebSocket.
  - Event Socket Library (ESL) for outbound control.
  - Automatic call recording, searchable from the dashboard.
- **Features:** barge-in / whisper / listen for supervisors; warm transfer with full transcript + summary; IVR fallback if AI is down.

## 3. Real-time audio bridge

**Best option: AudioSocket / custom WebSocket bridge.**

- FreeSWITCH streams raw audio chunks (e.g. 20 ms PCM) to the AI service.
- AI service returns TTS audio chunks in real time.
- Persistent bidirectional connection per call (session UUID tracking).

Alternative: WebRTC softphones for agents via LiveKit or equivalent. Stick with SIP for PSTN customers.

## 4. AI core service (the brain)

**Tech stack**

- Framework: Python + FastAPI (async) + LangGraph (stateful workflows, tool calling, memory)
- VAD: Silero or WebRTC VAD — detect end-of-utterance
- STT: `faster-whisper` (large-v3 or Nepali-tuned) on GPU, streaming partial transcripts
- LLM: Ollama with a strong model (Llama 3.1 70B or Qwen 2.5 72B fine-tuned on ISP data), tool calling:
  - `get_customer_info(customer_id)`
  - `check_router_status(ont_id)`
  - `create_ticket(...)`
  - `assign_field_team(location)`
  - `send_sms(...)`
- TTS: Piper TTS (fast, local), custom DishHome-branded Nepali voice, streamed sentence-by-sentence
- Orchestration: LangGraph manages multi-turn context, tool results, escalation logic

**Streaming pipeline for low latency**

1. Customer speaks → STT streams partial text.
2. On VAD end-of-utterance → send final transcript + context to LLM.
3. LLM streams tokens → TTS starts speaking as soon as first sentence is ready.
4. Play TTS audio back via FreeSWITCH while LLM continues generating.

**Expected latencies (self-hosted)**

| Stage                  | Time         |
| ---------------------- | ------------ |
| STT                    | 150 – 400 ms |
| LLM (tool call, 1st token) | 400 – 800 ms |
| TTS                    | 50 – 150 ms  |
| **Total turn**         | **700 – 1200 ms** |

## 5. Integration with ISP systems

The AI must be a **smart agent, not a chatbot**. Expose secure internal APIs:

- Billing / CRM (customer info, balance, package)
- Network OSS (ONT/ONU status, signal levels, outages)
- Ticketing (auto-create + assign)
- Field-team dispatch / SMS gateway

Authentication: API keys + mTLS.

**Example conversation flow — "router offline":**

1. Greet + identify customer (phone number or ask for ID).
2. Fetch account + device info in background.
3. Diagnose (tool call).
4. If fixable remotely → guide or remote reboot.
5. Else → create ticket, assign team, give ETA, confirm via SMS.

## 6. Monitoring, scaling, reliability

- **Redis** — call session state + queue.
- **PostgreSQL** — logs, recording metadata, analytics.
- **Prometheus + Grafana** — real-time dashboards (latency, success, escalation %).
- **Kubernetes** — auto-scale AI services.
- **Fallback** — low AI confidence or complex issue → seamless human transfer with summary.
- **Call recording** — encrypted, searchable from super admin.

## 7. Hardware suggestion (start)

- 2–4 high-end GPU servers (A100 / H100 or RTX 4090) for STT + LLM + TTS.
- FreeSWITCH on separate reliable servers.
