from threading import Lock

_MAX_EMAILS_OVERRIDE: int | None = None
_lock = Lock()


def set_max_emails_override(value: int) -> int:
    """Set process-local max emails override for worker runs."""
    global _MAX_EMAILS_OVERRIDE
    with _lock:
        _MAX_EMAILS_OVERRIDE = value
        return _MAX_EMAILS_OVERRIDE


def get_max_emails_override() -> int | None:
    """Return process-local max emails override if set."""
    with _lock:
        return _MAX_EMAILS_OVERRIDE


def clear_max_emails_override() -> None:
    """Clear process-local max emails override."""
    global _MAX_EMAILS_OVERRIDE
    with _lock:
        _MAX_EMAILS_OVERRIDE = None


def get_effective_max_emails(default_value: int) -> int:
    """Return override when present, otherwise the provided default."""
    override = get_max_emails_override()
    return override if override is not None else default_value
