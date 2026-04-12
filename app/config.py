from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Email / IMAP
    email_user: str
    email_pass: str
    imap_server: str = "imap.comcast.net"
    email_limit: int = 10

    # Database
    database_url: str

    # LLM — set to "groq" for production, "ollama" for local dev
    llm_provider: str = "ollama"
    groq_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
