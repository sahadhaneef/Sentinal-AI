"""Security utilities: session management, CSRF, actor identity."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from .config import get_settings

if TYPE_CHECKING:
    pass


_PROTOTYPE_ACTOR = "demo_reviewer"
_SESSION_COOKIE = "sentinel_session"
_CSRF_COOKIE = "csrf_token"
_CSRF_HEADER = "X-CSRF-Token"


def _sign(value: str) -> str:
    key = get_settings().secret_key.encode()
    sig = hmac.new(key, value.encode(), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"


def _verify_signature(signed: str) -> str | None:
    parts = signed.rsplit(".", 1)
    if len(parts) != 2:
        return None
    value, sig = parts
    expected = _sign(value).rsplit(".", 1)[1]
    if not hmac.compare_digest(sig, expected):
        return None
    return value


def create_session_token(actor_id: str = _PROTOTYPE_ACTOR) -> str:
    ts = int(time.time())
    raw = f"{actor_id}:{ts}"
    return _sign(raw)


def decode_session_token(token: str, max_age: int = 86400) -> str | None:
    raw = _verify_signature(token)
    if not raw:
        return None
    parts = raw.split(":", 1)
    if len(parts) != 2:
        return None
    actor_id, ts_str = parts
    if int(time.time()) - int(ts_str) > max_age:
        return None
    return actor_id


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def get_current_actor(request: Request) -> str | None:
    """Extract actor from signed session cookie.

    In development mode, falls back to demo_reviewer if not authenticated.
    Outside development mode, returns None if unauthenticated.
    """
    settings = get_settings()
    raw_session = request.cookies.get(_SESSION_COOKIE, "")
    if raw_session:
        actor = decode_session_token(raw_session, settings.session_max_age_seconds)
        if actor:
            return actor
    if settings.is_development:
        return _PROTOTYPE_ACTOR
    return None


def require_actor(request: Request) -> str:
    """Dependency: returns actor or raises 401."""
    actor = get_current_actor(request)
    if not actor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return actor


def verify_csrf(request: Request) -> None:
    """Verify CSRF token for mutations. Raises 403 on failure."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if request.url.path.endswith("/auth/login") or request.url.path.endswith("/auth/logout"):
        return
    csrf_header = request.headers.get(_CSRF_HEADER, "")
    csrf_cookie = request.cookies.get(_CSRF_COOKIE, "")
    if not csrf_header and not csrf_cookie and get_settings().is_development:
        return
    if not csrf_cookie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF cookie.")
    if not csrf_header or not hmac.compare_digest(csrf_header, csrf_cookie):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch or missing header.")


async def check_idempotency(db, key: str | None):
    """Check if an idempotency key was previously processed."""
    if not key:
        return None
    from sqlalchemy import select

    from ..db.models import IdempotencyRecord
    return await db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.key == key))


async def record_idempotency(db, key: str | None, endpoint: str, actor_id: str, status_code: int, response_json: str):
    """Record processed idempotency key."""
    if not key:
        return
    from ..db.models import IdempotencyRecord
    rec = IdempotencyRecord(
        key=key,
        endpoint=endpoint,
        actor_id=actor_id,
        response_status=status_code,
        response_json=response_json,
    )
    db.add(rec)
    await db.commit()
