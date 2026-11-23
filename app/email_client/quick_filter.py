"""Pre-screen before the LLM. See application_signals for what passes."""

from app.email_client.application_signals import should_classify


def quick_filter(sender: str, subject: str, email_content: str) -> bool:
    """
    Fast pre-screen before sending to LLM.
    Returns True if the email is worth classifying, False if it can be skipped.
    Keeps LLM call count low by catching obvious non-application emails early.
    """
    return should_classify(sender, subject, email_content)
