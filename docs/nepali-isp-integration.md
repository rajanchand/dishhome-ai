# Integrating with a Nepali ISP — practical guide

This document is the on-ramp for plugging the DishHome AI Call Center into a real Nepali ISP back-office (telephony, billing, OSS, ticketing, SMS, compliance). It assumes you've already read [telephony-architecture.md](telephony-architecture.md).

## 1. Telephony

### SIP trunk options (Nepal)

| Provider | Notes |
| --- | --- |
| **Nepal Telecom (NTC)** | National incumbent. Offers DID + toll-free numbers (`1660…`) and SIP trunks. Apply via the corporate sales desk. |
| **Ncell** | Mobile-first, also offers SIP trunks for enterprise. Good DID coverage. |
| **WorldLink / Vianet / Subisu** | Many ISPs offer business SIP trunks bundled with internet leased lines. |
| **Twilio / Plivo (international)** | Useful for failover and for testing from outside Nepal; latency is higher. |

The toll-free number on the architecture doc (`16600122000`) is an NTC short-code class.

### Codec + audio settings

| Setting | Value |
| --- | --- |
| Preferred codec | **PCMU (G.711 µ-law)** for trunks; transcoded to 16 kHz PCM internally for STT. |
| Sample rate | Internal pipeline 16 kHz mono 16-bit PCM. |
| Echo cancellation | Enabled in FreeSWITCH (`mod_echo` + `aec`). |
| Comfort noise | Disabled (Whisper handles silence well; comfort noise confuses VAD). |
| DTMF | RFC 2833 / SIP INFO — needed for IVR fallback and call-quality survey. |

### FreeSWITCH dialplan sketch

```xml
<extension name="dishhome-ai">
  <condition field="destination_number" expression="^16600122000$">
    <action application="answer"/>
    <action application="set" data="record_session=true"/>
    <action application="set" data="recording_path=/recordings/${uuid}.wav"/>
    <action application="audio_socket" data="ai-core.dishhome.local:4000 ${uuid}"/>
    <action application="hangup"/>
  </condition>
</extension>
```

`audio_socket` opens a TCP connection to the backend audio server (`backend/app/audio_server.py` in Phase 2). Backend reads 8 kHz µ-law frames, upsamples to 16 kHz PCM, feeds VAD → STT → LLM → TTS, and writes back the same way.

### Failover / IVR fallback

If the AI core is unreachable (health check fails) FreeSWITCH should fall through to a static IVR that announces wait time and queues to a human agent. Implement as a second `condition` below the AI bridge.

## 2. Billing / CRM integration

Most Nepali ISPs run one of:

| Stack | Notes |
| --- | --- |
| **Freeside** | Open-source telecom billing. Has a JSON-RPC API; expose internally and call from `routers/integrations.py`. |
| **Splynx** | Common WISP/ISP billing. REST API, OAuth2. |
| **Custom PHP/Laravel CRM** | Many ISPs in Nepal run an in-house system. Add a thin adapter in `backend/app/integrations/billing_<vendor>.py`. |

### Recommended adapter shape

Replace the mocked `find_customer()` in `backend/app/mock_data.py` with a function in a new module `backend/app/integrations/billing.py`:

```python
async def find_customer(query: str) -> Customer | None:
    async with httpx.AsyncClient(timeout=2.0) as client:
        r = await client.get(
            f"{settings.billing_api_base_url}/api/customers/{query}",
            headers={"Authorization": f"Bearer {settings.billing_api_key}"},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return Customer.model_validate(r.json())
```

Wrap external calls with circuit-breaker / retry (use `tenacity`) and a 2 s timeout — voice latency budget is unforgiving.

### Fields the AI agent needs

- Customer ID, mobile, smartcard
- Active package + monthly fee
- Outstanding balance, next due date
- Assigned ONT ID / device serial
- Service address with **ward + pincode** (drives field-team routing)
- Service status (`active`, `suspended`, `overdue`)
- Preferred language (Nepali vs English)

## 3. Network OSS / ONT diagnostics

ISPs in Nepal typically use **Huawei / ZTE OLTs** with TR-069 or vendor APIs for ONT control.

### Common upstream systems

| System | What to query |
| --- | --- |
| **Huawei iManager U2000** | ONT status, RX/TX power, uptime, port state |
| **ZTE NetNumen U31** | Same as above |
| **PPPoE / RADIUS (FreeRADIUS)** | Active session, last login, total uptime |
| **NMS (Zabbix / LibreNMS)** | Area outage flags, BNG health |

### Adapter shape

`backend/app/integrations/oss.py`:

```python
async def router_status(ont_id: str) -> RouterStatus:
    # Pull from your OLT inventory + RADIUS in parallel
    ont_task = client.get(f"{olt_api}/onts/{ont_id}")
    pppoe_task = client.get(f"{radius_api}/sessions?ont_id={ont_id}")
    outage_task = client.get(f"{nms_api}/outages?ont_id={ont_id}")
    ont, pppoe, outages = await asyncio.gather(ont_task, pppoe_task, outage_task)
    return RouterStatus(...)
```

### What "router offline" actually means in Nepal

In >70% of real cases the problem is one of:
1. **PPPoE session expired** — fix with remote reauth.
2. **Area outage** (power cut, fiber cut, OLT down) — surface to the customer, ETA from NMS.
3. **ONT physically powered off** — guide the customer through reboot.
4. **Low RX power (< -27 dBm)** — fiber dirty or bent. Dispatch field team.

The AI's diagnostic flow should branch on these four buckets.

## 4. Field-team dispatch

Most ISPs route field tasks via a mobile app (often Odoo, custom Flutter, or a Google Sheet for smaller ISPs). Expose dispatch via REST:

```python
POST /dispatch/assign
{ "ticket_id": "DH-T-44219", "ward": "Lakeside-15", "priority": "high" }
```

Pincode → team mapping should live in a small `dispatch_zones` table keyed by `(province, district, ward)`. ETA is `team.queue_length × average_resolution_time`.

## 5. SMS gateway

| Provider | Notes |
| --- | --- |
| **Sparrow SMS** | Most common in Nepal. REST API, supports sender ID approval. |
| **Sociair SMS** | Bulk + transactional. |
| **NT BulkSMS** | NTC-operated. Reliable for transactional. |

Wrap in `backend/app/integrations/sms.py`:

```python
async def send_sms(to: str, body: str) -> None:
    await client.post(
        settings.sms_gateway_url,
        params={"token": settings.sms_gateway_api_key, "from": "DISHHOME", "to": to, "text": body},
    )
```

Templates the AI should send:
- Ticket created: `DishHome: Ticket {id} cha. ETA {eta} minute. Field team: {team}.`
- Reboot success: `DishHome: Tapainko router reboot bhayo. Aaba chalcha. Dhanyabad.`
- Outage: `DishHome: {area} ma area outage cha. Restoration ETA: {eta}. Dhanyabad.`

## 6. Compliance & operational concerns

### Call recording

- **NTA** (Nepal Telecommunications Authority) does not currently mandate recording, but does require call-data retention for **6 months**. Store call metadata (number → number, duration, outcome) — NOT the audio — for 6 months minimum.
- For audio recordings, get explicit consent in the greeting: *"Yo call quality ko lagi record garincha."*
- Retain audio max **90 days** unless legally required; PII redaction recommended.

### Data residency

NTA prefers customer PII to live in-country. If you're using cloud, prefer **AWS Mumbai (ap-south-1)** or local Nepali datacenters (Bhrikuti Networks, Silver Lining, NTC IDC). Don't ship raw call audio to OpenAI / cloud LLMs without a redaction layer.

### KYC / authentication during call

For account changes (package upgrade, address change), the AI must verify identity:
1. Confirm customer ID + registered mobile.
2. Send OTP to registered mobile.
3. Customer reads OTP back — agent verifies.

The AI must NEVER expose: full smartcard number, password hash, payment card data.

### Languages

- Default to Nepali. Detect language from the first customer utterance (faster-whisper returns language tag).
- Switch to English on request or if the model's language detection drops below 0.7 confidence in Nepali.
- Numbers in Nepali should be spoken **digit-by-digit** for IDs (eg. "DH-one-zero-zero-two-three-four"), full-word for amounts ("paanchhsay rupaiya").

## 7. Performance budget

Voice agents are unforgiving. Target end-to-end turn latency:

| Stage | p95 target |
| --- | --- |
| STT (streaming, end-of-utterance) | < 400 ms |
| LLM first token (with one tool call) | < 800 ms |
| TTS first audio chunk | < 200 ms |
| **Total turn** | **< 1.4 s** |

Network round-trips to upstream ISP systems (billing, OSS) **must be under 250 ms p95**. Cache aggressively (5-minute TTL in Redis for customer lookups).

Monitor with the `/metrics` endpoint already wired in this scaffold — it surfaces p50/p95/p99 per route and error rate. Export to Prometheus in production.

## 8. Where to add code

| What you're integrating | Where it goes |
| --- | --- |
| Billing API | `backend/app/integrations/billing.py` (new) — import from `routers/integrations.py` |
| OSS / ONT control | `backend/app/integrations/oss.py` (new) |
| SMS gateway | `backend/app/integrations/sms.py` (new) |
| FreeSWITCH dialplan | `telephony/dialplan/ai_bridge.xml` (new) |
| AudioSocket server | `backend/app/audio_server.py` (new) |
| Tool calls the LLM can make | `backend/app/llm/tools.py` (new) — keep small; one function per capability |

Replace mock dicts in `backend/app/mock_data.py` with real adapters one at a time; the API surface stays identical, so the frontend doesn't change.
