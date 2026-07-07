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
    imap_server: str = "imap.gmail.com"

    # Worker knobs — tunable via env without code changes.
    # EMAIL_LIMIT is preserved for backward-compat; MAX_EMAILS_PER_RUN is preferred.
    email_limit: int = 5
    imap_timeout_seconds: int = 30
    max_emails_per_run: int = 10
    stale_run_ttl_minutes: int = 1440  # 24 hours

    # Database
    database_url: str

    # LLM — set to "groq" for production, "ollama" for local dev
    llm_provider: str = "groq"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    # JWT — set JWT_SECRET to a long random string in production
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 1440

    # Rate limiting (slowapi) — per-IP for public/login, per-user when authenticated
    rate_limit_enabled: bool = True
    rate_limit_login: str = "10/minute"
    rate_limit_public: str = "60/minute"
    rate_limit_global: str = "120/minute"
    rate_limit_expensive: str = "10/minute"

    @field_validator("imap_timeout_seconds")
    @classmethod
    def _positive_timeout(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("IMAP_TIMEOUT_SECONDS must be a positive integer")
        return v

    @field_validator("email_limit")
    @classmethod
    def _positive_email_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("EMAIL_LIMIT must be a positive integer")
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
        model_part = f" groq_model={self.groq_model}" if self.llm_provider == "groq" else ""
        return (
            f"provider={self.llm_provider}{model_part} imap_server={self.imap_server} "
            f"imap_timeout={self.imap_timeout_seconds}s "
            f"email_limit={self.email_limit} max_emails={self.max_emails_per_run} "
            f"stale_ttl={self.stale_run_ttl_minutes}m"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
