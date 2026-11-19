class LLMProviderError(RuntimeError):
    """Raised when the upstream LLM provider call fails."""


class LLMResponseError(RuntimeError):
    """Raised when provider output cannot be normalized."""


class FinderError(RuntimeError):
    """User-facing job-finder failure. `status_code` is returned by the API."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code
