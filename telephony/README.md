# Telephony — FreeSWITCH

This folder holds FreeSWITCH configuration (dialplan, SIP profiles, AudioSocket bridge) for routing PSTN/SIP calls into the AI core service. Empty for now — see `dialplan/.gitkeep`.

## Planned files

```
telephony/
├── dialplan/
│   ├── ai_bridge.xml         Route to AI extension, bridge audio via AudioSocket
│   └── ivr_fallback.xml      Fallback IVR if AI core is down
├── sip_profiles/
│   └── external.xml          SIP trunk to NTC / Ncell / provider
└── scripts/
    └── start_audiosocket.sh  Start audiosocket server on container boot
```

## How it plugs in

1. SIP trunk delivers an inbound call to FreeSWITCH.
2. Dialplan routes to the AI bridge extension.
3. `mod_audiosocket` (or equivalent) opens a TCP/WebSocket to the backend at `${FREESWITCH_AUDIOSOCKET_HOST}:${FREESWITCH_AUDIOSOCKET_PORT}`.
4. Backend streams PCM → STT → LLM → TTS → PCM back to FreeSWITCH.
5. On escalation, FreeSWITCH performs a warm transfer to a human agent extension with the conversation summary attached.

See [../docs/telephony-architecture.md](../docs/telephony-architecture.md) for the full design.
