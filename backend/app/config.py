from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_log_level: str = "info"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    cors_allowed_origins: str = "http://localhost:5173"

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:70b"

    redis_host: str = "localhost"
    redis_port: int = 6379

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "dishhome_ai"
    postgres_user: str = "dishhome"
    postgres_password: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()
