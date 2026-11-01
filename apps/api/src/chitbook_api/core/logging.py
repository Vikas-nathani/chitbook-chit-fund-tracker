"""Structured JSON logging to stdout (read it with `docker compose logs api`; no log files).

Every line carries: timestamp (IST), level, event, logger, request_id, user_id (when known).
Sensitive keys are redacted before anything is written.
"""

from __future__ import annotations

import logging
import sys
from typing import IO, Any

import structlog
from structlog.typing import EventDict, WrappedLogger

from chitbook_api.core.config import Settings
from chitbook_api.core.time import now

SENSITIVE_KEYS = {
    "password",
    "current_password",
    "new_password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "secret",
    "jwt_secret",
}


def _redact(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    for key in list(event_dict):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "***"
    return event_dict


def _ist_timestamp(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    event_dict["timestamp"] = now().isoformat(timespec="milliseconds")
    return event_dict


class _StdoutHandler(logging.StreamHandler[IO[str]]):
    """Writes to whatever sys.stdout is at write time (so pytest's capsys sees the lines)."""

    def __init__(self) -> None:
        super().__init__(sys.stdout)

    @property
    def stream(self) -> IO[str]:
        return sys.stdout

    @stream.setter
    def stream(self, _: IO[str]) -> None:
        pass


def configure_logging(settings: Settings) -> None:
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _ist_timestamp,
        _redact,
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = _StdoutHandler()
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Our middleware writes one access line per request; silence uvicorn's duplicate
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
