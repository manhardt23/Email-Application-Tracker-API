import ollama

from app.llm.base import EmailClassification
from app.llm.errors import LLMProviderError, LLMResponseError
from app.llm.normalization import extract_json_object, normalize_classification

_PROMPT = """\
Analyze this email to determine if it's about a job application
that the recipient has ALREADY SUBMITTED.

IMPORTANT: Classify as an application ONLY if the email:
- Confirms receipt of an application the user submitted
- Provides status updates on an existing application (interview, assessment, offer, rejection)
- Requests action on an existing application (complete assessment, schedule interview)
- Is a direct response to an application the user sent

DO NOT classify as an application if the email:
- Is a job posting or job alert about new openings
- Promotes new opportunities the user hasn't applied to
- Is a newsletter about available positions
- Invites the user to apply to a new position they haven't applied to yet
- Is marketing or promotional content

Email:
From: {sender}
Subject: {subject}
Body: {body}

Return ONLY valid JSON with no explanation:
{{
    "is_application": boolean,
    "stage": "applied|rejected|interview|offer|assessment|other or null",
    "company": "string or null",
    "position": "string or null",
    "confidence": "high|medium|low"
}}
"""


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
            print(content)
            return normalize_classification(extract_json_object(content))
        except LLMResponseError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMProviderError(
                f"Ollama classification failed with model {self.model}."
            ) from exc
