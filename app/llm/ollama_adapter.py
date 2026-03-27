import json
import re

import ollama

from app.email_client.quick_filter import quick_filter
from app.llm.base import EmailClassification

_PROMPT = """\
Analyze this email to determine if it's about a job application that the recipient has ALREADY SUBMITTED.

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
    def __init__(self, model: str = "llama3") -> None:
        self.model = model

    def classify_email(
        self, sender: str, subject: str, body: str
    ) -> EmailClassification | None:
        if not quick_filter(sender, subject, body):
            print("Quick filter: not an application email, skipping LLM")
            return None

        prompt = _PROMPT.format(sender=sender, subject=subject, body=body[:2000])
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response["message"]["content"]
        print(content)

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            print("No JSON found in LLM response")
            return None

        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM JSON: {e}")
            return None

        if not isinstance(data, dict):
            return None

        return EmailClassification(
            is_application=bool(data.get("is_application", False)),
            company=data.get("company"),
            position=data.get("position"),
            stage=data.get("stage"),
            confidence=data.get("confidence", "low"),
        )
