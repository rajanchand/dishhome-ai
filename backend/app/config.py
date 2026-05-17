from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus


class ConfigurationError(RuntimeError):
    """Raised when required deployment configuration is missing or unsafe."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_log_level: str = "info"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    sentry_dsn: str = ""

    # Secret key for CSRF tokens / cookie signing. Generate with:
    #   python -c "import secrets; print(secrets.token_urlsafe(64))"
    app_secret_key: str = ""

    # Public origin the backend is reachable at (ngrok URL in dev, real domain in prod).
    # Used to build absolute URLs in webhooks (Twilio fetches TwiML from this).
    public_base_url: str = ""

    # SECURITY: Pin to exact deployment domains. Never use wildcards in production.
    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "https://dishhome-ai-8hxd.vercel.app"
    )

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:70b"

    freeswitch_audiosocket_host: str = "0.0.0.0"
    freeswitch_audiosocket_port: int = 4000
    enable_audio_server: bool = False

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
    supabase_schema: str = "dh"
    
    # Postgres Direct & Pooling URLs
    database_url: str = ""
    direct_url: str = ""

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def effective_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if not (self.postgres_host and self.postgres_db and self.postgres_user and self.postgres_password):
            return ""
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        host = self.postgres_host
        return f"postgresql://{user}:{password}@{host}:{self.postgres_port}/{self.postgres_db}"

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

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_for_runtime(self) -> None:
        """Fail fast on unsafe production settings.

        Development should stay easy to run, but production should never boot
        with placeholder secrets, missing persistence, or loose callback auth.
        """
        if not self.is_production:
            return

        errors: list[str] = []
        if len(self.app_secret_key.strip()) < 32:
            errors.append("APP_SECRET_KEY must be set to at least 32 characters")
        if not self.public_base_url.startswith("https://"):
            errors.append("PUBLIC_BASE_URL must be an https URL in production")
        if not self.effective_database_url:
            errors.append("DATABASE_URL or POSTGRES_* settings must be set in production")
        if not self.twilio_validate_signatures:
            errors.append("TWILIO_VALIDATE_SIGNATURES must remain true in production")
        origins = self.cors_origins_list
        if not origins:
            errors.append("CORS_ALLOWED_ORIGINS must include the deployed frontend origin")
        for origin in origins:
            if "*" in origin:
                errors.append("CORS_ALLOWED_ORIGINS must not contain wildcards")
            if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
                errors.append("CORS_ALLOWED_ORIGINS must not contain localhost in production")

        if errors:
            raise ConfigurationError("; ".join(errors))


settings = Settings()
