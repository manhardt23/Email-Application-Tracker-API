"""
Logging configuration for the worker process.

Call configure_logging() once at process startup (in main()). The format is
intentionally grep-friendly: ISO timestamp, level, logger name, and message on
one line. worker_run_id is injected per log call via the 'extra' dict rather than
a filter, keeping the setup simple.

LOG_LEVEL env var controls verbosity (default: INFO). Accepted values are the
standard Python level names: DEBUG, INFO, WARNING, ERROR, CRITICAL.
"""
import logging
import os


def configure_logging() -> None:
    """Configure root logger for the worker process."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Silence noisy third-party loggers at WARNING unless DEBUG is requested.
    if level > logging.DEBUG:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("groq").setLevel(logging.WARNING)
