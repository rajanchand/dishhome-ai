# DishHome AI Call Center — local setup & deployment

Everything is wired and degrades gracefully without keys: the UI runs, mock
data flows, but the demo call returns a "configure Twilio" hint instead of
ringing your phone. Adding the four `.env` blocks below switches it to real.

---

## 1. One‑time install

```sh
# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Tools (macOS)
brew install ngrok
ngrok config add-authtoken <your-token-from-ngrok.com>
```

Copy the example env:

```sh
cp backend/.env.example backend/.env
```

---

## 2. Get accounts + keys (~10 min)

### Twilio (outbound calling)
1. Sign up at <https://twilio.com> — free trial gives ~$15 credit.
2. Console → **Account info** → copy `Account SID` and `Auth Token` into
   `backend/.env` as `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN`.
3. Buy a number: Console → **Phone Numbers → Buy a number**. Pick any
   country; UK/US numbers are cheapest for outbound. Paste it into
   `backend/.env` as `TWILIO_FROM_NUMBER` (E.164, e.g. `+447400000000`).
4. **Verify your test mobile**: Console → **Phone Numbers → Verified
   Caller IDs → Add a new Caller ID**. Enter `+447570731478`, Twilio will
   call/SMS a 6-digit code. Trial accounts can only call verified numbers.
5. Free demo numbers to receive calls (no verification needed):
   - <https://onlinesim.io> — disposable inbound numbers
   - Your own SIP softphone (Zoiper, Linphone) registered to a free SIP
     provider (e.g. iptel.org).

### ElevenLabs (voice cloning + TTS)
1. Sign up at <https://elevenlabs.io>.
2. Profile → **API key** → copy into `.env` as `ELEVENLABS_API_KEY`.
3. For *Instant Voice Clone* (Bibek / Priya / your own voice): the Creator
   plan ($22/mo) unlocks it. Free tier still gives you TTS over their
   pre-built voices.
4. Pick four default voice IDs (one per language/gender) from the
   ElevenLabs **Voice Library**; paste into:
   ```
   ELEVENLABS_VOICE_NE_FEMALE=...
   ELEVENLABS_VOICE_NE_MALE=...
   ELEVENLABS_VOICE_EN_FEMALE=...
   ELEVENLABS_VOICE_EN_MALE=...
   ```
   (For Nepali, use a multilingual voice that handles Devanagari well;
   `eleven_multilingual_v2` is the recommended model and already the
   default in `.env`.)

You can also upload a 1‑minute clean sample of your own voice via the UI
(**Voice Lab → Clone**) — the backend will create the ElevenLabs voice
and return its `voice_id`, which you then paste into the env above so it
becomes a default for that language/gender.

---

## 3. Run the stack

```sh
./scripts/dev.sh
```

That boots:
- backend on <http://localhost:8000>
- frontend on <http://localhost:3000>
- an ngrok tunnel to backend `:8000` for Twilio webhooks

When ngrok prints its `https://*.ngrok-free.app` URL, **paste it into
`backend/.env` as `PUBLIC_BASE_URL=...` and restart** (Ctrl-C and re-run
`./scripts/dev.sh`). Twilio fetches TwiML and posts status callbacks from
that URL.

---

## 4. End-to-end test (rings your phone)

1. Open <http://localhost:3000>, log in (`admin` / `dishhome123`).
2. **Campaigns → pick one → Demo call**.
3. Enter `+447570731478` (E.164, with `+44` country code; drop the
   leading `0`). Click **▶ Demo call**.
4. Your phone rings. Twilio plays the campaign script in the configured
   voice. The UI polls `/telephony/sessions/{sid}` and shows live status
   (queued → ringing → in-progress → completed).

If you see "Running in mock mode", `TWILIO_*` or `PUBLIC_BASE_URL` is
missing — check `curl http://localhost:8000/telephony/health` to see
which.

---

## 5. Access portal

`/admin/access` (super_admin / admin only). Create users, assign roles,
reset passwords. Role → permission mapping is fixed in `backend/app/rbac.py`
for auditability — to change it edit that file.

Default seed users (password `dishhome123` for all):
- `admin` — super_admin
- `supervisor` — supervisor
- `agent` — agent

---

## 6. Production deployment notes

- Replace in-memory `_SESSIONS` and `USERS` with a real DB + hashed passwords.
- Replace in-memory `SESSIONS` in `telephony.py` with Redis or Postgres.
- Put backend behind a reverse proxy (nginx/Caddy) with HTTPS — Twilio
  *requires* HTTPS for webhook URLs.
- Rotate `TWILIO_AUTH_TOKEN` and `ELEVENLABS_API_KEY` regularly; never log
  them.
- The TwiML/status webhooks are currently unauthenticated (Twilio doesn't
  send a bearer token). Add Twilio's request signature validation in
  prod (`X-Twilio-Signature` header).
- For Nepal-specific deployment: an NTC/Ncell SIP trunk gets you native
  local numbers and bypasses Twilio international rates, but requires NTA
  approval. See `docs/nepali-isp-integration.md`.
