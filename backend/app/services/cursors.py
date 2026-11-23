"""Opaque continuation tokens bound to one filtered result snapshot and server lifetime."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.errors import ApiError


class CursorCodec:
    """Signed prototype cursors expire after 15 minutes or a server restart."""

    def __init__(self, key: bytes) -> None:
        self.key = key

    def encode(self, query: str, snapshot: str, anchor: str) -> str:
        body = json.dumps(
            {"q": query, "s": snapshot, "a": anchor, "exp": int(time.time()) + 900},
            separators=(",", ":"),
        ).encode()
        signature = hmac.digest(self.key, body, "sha256")
        return base64.urlsafe_b64encode(body + signature).decode().rstrip("=")

    def decode(self, token: str, query: str, snapshot: str) -> str:
        try:
            raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
            body, signature = raw[:-32], raw[-32:]
            if not hmac.compare_digest(hmac.digest(self.key, body, "sha256"), signature):
                raise ValueError("Invalid signature")
            values = json.loads(body)
            if (
                values["q"] != query
                or values["s"] != snapshot
                or values["exp"] < time.time()
                or not isinstance(values["a"], str)
            ):
                raise ValueError("Stale cursor")
            return values["a"]
        except (ValueError, KeyError, TypeError):
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                "This cursor is invalid or stale. Restart from the first page.",
            ) from None


def digest_json(value: Any) -> str:
    """Fingerprint normalized filters and persisted snapshot data deterministically."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()
