"""
Groq LLM adapter — implemented in Phase 4.
Requires: GROQ_API_KEY set in environment / .env
Model: llama-3.1-8b-instant (free tier, 14,400 req/day, 30 req/min)
"""
from app.llm.base import EmailClassification


class GroqAdapter:
    def classify_email(
        self, sender: str, subject: str, body: str
    ) -> EmailClassification | None:
        raise NotImplementedError(
            "Groq adapter not yet implemented. Set LLM_PROVIDER=ollama for local dev. "
            "See Phase 4 for full Groq implementation."
        )
