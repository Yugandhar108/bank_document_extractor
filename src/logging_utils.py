"""Application logging with protection against accidental sensitive-data logging."""

from __future__ import annotations

import logging
from pathlib import Path
import re
from contextvars import ContextVar
from typing import Any
from uuid import uuid4


_SECRET_PATTERN = re.compile(
    r"(?i)(?:authorization\s*[:=]\s*)?bearer\s+[^\s,;]+|"
    r"(api[_ -]?key|authorization|token|password|secret)\s*[:=]\s*[^\s,;]+"
)
_current_run_id: ContextVar[str] = ContextVar("current_run_id", default="system")


def new_run_id() -> str:
    """Create a short identifier safe to show to a user."""
    return uuid4().hex[:12]


def set_run_id(run_id: str):
    """Set the run ID used by log events in the current execution context."""
    return _current_run_id.set(run_id)


def reset_run_id(token) -> None:
    """Restore the previous run ID."""
    _current_run_id.reset(token)


def _safe_message(message: str) -> str:
    return _SECRET_PATTERN.sub(r"\1=[REDACTED]", message)


class RedactingFormatter(logging.Formatter):
    """Remove common secret-shaped values before writing a log record."""

    def format(self, record: logging.LogRecord) -> str:
        return _safe_message(super().format(record))


def get_app_logger(log_directory: Path | None = None) -> logging.Logger:
    """Return the application logger configured for the local logs directory."""
    directory = log_directory or Path(__file__).resolve().parents[1] / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("bank_document_extractor")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = directory / "application.log"
    configured_path = getattr(logger, "_configured_log_path", None)
    if configured_path != log_path:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(
            RedactingFormatter("%(asctime)s %(levelname)s run=%(run_id)s %(message)s")
        )
        logger.addHandler(handler)
        logger._configured_log_path = log_path

    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    message: str,
    run_id: str = "system",
    **details: Any,
) -> None:
    """Write a structured, non-sensitive diagnostic event."""
    active_run_id = run_id if run_id != "system" else _current_run_id.get()
    safe_details = " ".join(
        f"{key}={_safe_message(str(value))}" for key, value in details.items()
    )
    logger.log(level, "%s%s", message, f" {safe_details}" if safe_details else "", extra={"run_id": active_run_id})