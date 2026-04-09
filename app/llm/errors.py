class LLMProviderError(RuntimeError):
    """Raised when the upstream LLM provider call fails."""


class LLMResponseError(RuntimeError):
    """Raised when provider output cannot be normalized."""
