"""
Groq LLM adapter — implemented in Phase 4.
Requires: GROQ_API_KEY set in environment / .env
Default model: openai/gpt-oss-120b (override via GROQ_MODEL)
"""
from app.llm.base import EmailClassification
from app.llm.errors import LLMProviderError, LLMResponseError
from app.llm.normalization import extract_json_object, normalize_classification
from app.llm.prompt import CLASSIFICATION_PROMPT as _PROMPT


class GroqAdapter:
    provider_name = "groq"

    def __init__(
        self,
        api_key: str | None,
        model: str = "openai/gpt-oss-120b",
    ) -> None:
        try:
            from groq import Groq
        except ModuleNotFoundError as exc:
            raise LLMProviderError(
                "Groq SDK is not installed. Install dependencies from requirements.txt."
            ) from exc
        if not api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER='groq'.")
        self.client = Groq(api_key=api_key)
        self.model = model

    @property
    def model_name(self) -> str:
        return self.model

    def classify_email(
        self, sender: str, subject: str, body: str
    ) -> EmailClassification | None:
        prompt = _PROMPT.format(sender=sender, subject=subject, body=body[:2000])
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            content = (response.choices[0].message.content or "").strip()
            return normalize_classification(extract_json_object(content))
        except LLMResponseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(
                f"Groq classification failed with model {self.model}."
            ) from exc
