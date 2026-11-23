import ollama

from app.llm.base import EmailClassification
from app.llm.errors import LLMProviderError, LLMResponseError
from app.llm.normalization import extract_json_object, normalize_classification
from app.llm.prompt import CLASSIFICATION_PROMPT as _PROMPT


class OllamaAdapter:
    provider_name = "ollama"

    def __init__(self, model: str = "llama3") -> None:
        self.model = model

    def classify_email(
        self, sender: str, subject: str, body: str
    ) -> EmailClassification | None:
        prompt = _PROMPT.format(sender=sender, subject=subject, body=body[:2000])
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response["message"]["content"]
            return normalize_classification(extract_json_object(content))
        except LLMResponseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(
                f"Ollama classification failed with model {self.model}."
            ) from exc
