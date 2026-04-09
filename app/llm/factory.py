from app.config import Settings
from app.llm.base import LLMClassifier


def build_classifier(settings: Settings) -> LLMClassifier:
    provider = settings.llm_provider.strip().lower()
    if provider == "groq":
        from app.llm.groq_adapter import GroqAdapter

        return GroqAdapter(api_key=settings.groq_api_key)
    if provider == "ollama":
        from app.llm.ollama_adapter import OllamaAdapter

        return OllamaAdapter()
    raise ValueError(
        "Invalid LLM_PROVIDER value: "
        f"{settings.llm_provider!r}. Expected one of: 'groq', 'ollama'."
    )
