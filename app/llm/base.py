from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmailClassification:
    is_application: bool
    company: str | None = None
    position: str | None = None
    stage: str | None = None
    confidence: str = "low"  # high / medium / low


class LLMClassifier(Protocol):
    provider_name: str

    def classify_email(
        self, sender: str, subject: str, body: str
    ) -> EmailClassification | None:
        ...
