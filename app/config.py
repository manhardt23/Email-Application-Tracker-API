from functools import lru_cache

from pydantic import field_validator
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

    # Worker knobs — tunable via env without code changes.
    # EMAIL_LIMIT is preserved for backward-compat; MAX_EMAILS_PER_RUN is preferred.
    email_limit: int = 10
    imap_timeout_seconds: int = 30
    max_emails_per_run: int = 50
    stale_run_ttl_minutes: int = 1440  # 24 hours

    # Database
    database_url: str

    # LLM — set to "groq" for production, "ollama" for local dev
    llm_provider: str = "ollama"
    groq_api_key: str | None = None

    @field_validator("imap_timeout_seconds")
    @classmethod
    def _positive_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("IMAP_TIMEOUT_SECONDS must be a positive integer")
        return v

    @field_validator("max_emails_per_run")
    @classmethod
    def _positive_max_emails(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("MAX_EMAILS_PER_RUN must be a positive integer")
        return v

    @field_validator("stale_run_ttl_minutes")
    @classmethod
    def _positive_ttl(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("STALE_RUN_TTL_MINUTES must be a positive integer")
        return v

    def safe_summary(self) -> str:
        """Return a one-line config summary safe to log (no secrets)."""
        return (
            f"provider={self.llm_provider} imap_server={self.imap_server} "
            f"imap_timeout={self.imap_timeout_seconds}s "
            f"max_emails={self.max_emails_per_run} "
            f"stale_ttl={self.stale_run_ttl_minutes}m"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
