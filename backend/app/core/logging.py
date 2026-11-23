import json
import logging
import re
import sys
from datetime import UTC, datetime

logger = logging.getLogger("sentinel")


def redact(text: str) -> str:
    """Defense in depth; request bodies, URLs, cookies and exceptions are never logged."""
    text = re.sub(r"(?i)bearer\s+[^\s,;]+", "Bearer [REDACTED]", text)
    text = re.sub(r"\b(?:sk-|ghp_|github_pat_)[\w-]{8,}", "[REDACTED]", text)
    return re.sub(
        r"(?i)\b(password|token|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+",
        r"\1=[REDACTED]",
        text,
    )


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        for name in ("request_id", "method", "route", "status", "duration_ms", "exception_type"):
            if hasattr(record, name):
                value = getattr(record, name)
                payload[name] = redact(value) if isinstance(value, str) else value
        # Deliberately do not serialize exc_info, request data or arbitrary log extras.
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str) -> None:
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.propagate = False
