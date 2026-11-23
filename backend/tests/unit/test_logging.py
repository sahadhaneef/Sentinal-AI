import json
import logging
from datetime import datetime

from app.core.logging import JsonFormatter, redact


def test_logs_are_structured_utc_and_do_not_serialize_exception_or_untrusted_extras():
    record = logging.LogRecord("sentinel", logging.ERROR, "", 0, "password=topsecret", (), None)
    record.request_id = "request-123"
    record.cookies = "session=private"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "request-123"
    assert payload["message"] == "password=[REDACTED]"
    assert "cookies" not in payload
    assert payload["timestamp"].endswith("Z")
    assert datetime.fromisoformat(payload["timestamp"]).utcoffset().total_seconds() == 0


def test_common_secret_shapes_are_redacted():
    safe = redact("Bearer private-token api_key=secret sk-proj-abcdefghijklmnop")
    assert "private-token" not in safe
    assert "=secret" not in safe
    assert "abcdefghijklmnop" not in safe
