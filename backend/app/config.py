from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_log_level: str = "info"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Secret key for CSRF tokens / cookie signing. Generate with:
    #   python -c "import secrets; print(secrets.token_urlsafe(64))"
    app_secret_key: str = ""

    # Public origin the backend is reachable at (ngrok URL in dev, real domain in prod).
    # Used to build absolute URLs in webhooks (Twilio fetches TwiML from this).
    public_base_url: str = ""

    # SECURITY: Pin to exact deployment domains. Never use wildcards in production.
    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://212.227.39.216:5173,"
        "https://dishhome-ai-8hxd.vercel.app"
    )

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:70b"

    redis_host: str = "localhost"
    redis_port: int = 6379

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "dishhome_ai"
    postgres_user: str = "dishhome"
    postgres_password: str = ""

    # ElevenLabs (voice cloning + TTS). When unset, voice endpoints fall back to
    # the browser Web Speech API spec they previously returned.
    elevenlabs_api_key: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    # Default ElevenLabs voice IDs for the four built-in personas. Override via .env
    # once you've created/cloned them in the ElevenLabs dashboard.
    elevenlabs_voice_ne_female: str = ""  # Anjali
    elevenlabs_voice_ne_male: str = ""    # Bibek
    elevenlabs_voice_en_female: str = ""  # Priya
    elevenlabs_voice_en_male: str = ""    # Arjun

    # Twilio (outbound calls + TwiML). When unset, /telephony endpoints return 503
    # with an actionable error explaining which env var is missing.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""  # e.g. "+15005550006" (Twilio test) or your real number
    # When False, /telephony webhooks accept unsigned requests (dev only).
    # Always True in production — the auth_token is then used to validate the
    # X-Twilio-Signature header.
    twilio_validate_signatures: bool = True

    # --- Supabase (Postgres-backed persistence via PostgREST) ---
    # When unset, the app uses its in-memory state (current behaviour).
    # When set, USERS / login events / audit log / sessions write through to
    # Supabase so they survive restarts and scale across instances.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_schema: str = "public"
    
    # Postgres Direct & Pooling URLs
    database_url: str = ""
    direct_url: str = ""

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def elevenlabs_enabled(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @property
    def twilio_enabled(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)

    def elevenlabs_voice_for(self, language: str, gender: str) -> str:
        return {
            ("ne", "female"): self.elevenlabs_voice_ne_female,
            ("ne", "male"): self.elevenlabs_voice_ne_male,
            ("en", "female"): self.elevenlabs_voice_en_female,
            ("en", "male"): self.elevenlabs_voice_en_male,
        }.get((language, gender), "")


settings = Settings()
