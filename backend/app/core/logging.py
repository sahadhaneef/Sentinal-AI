"""Structured JSON logging."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import UTC, datetime

from .config import get_settings


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def new_request_id() -> str:
    return str(uuid.uuid4())
