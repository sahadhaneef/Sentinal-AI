"""Validated persistence primitives; these do not change frontend wire types."""

import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_token(value: str, maximum: int = 128) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("Expected a portable opaque identifier")
    if len(value) > maximum or ".." in value:
        raise ValueError("Invalid identifier length or traversal sequence")
    return value


def validate_relative_key(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 512
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]*", value)
        or ".." in value
        or "//" in value
        or any(part in {"", ".", ".git"} or part.startswith(".env") for part in value.split("/"))
    ):
        raise ValueError("Expected a portable relative artifact/source key")
    return value


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("An aware timestamp is required")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None else None


class Token(TypeDecorator[str]):
    impl = String(128)
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return validate_token(value) if value is not None else None


class RelativeKey(TypeDecorator[str]):
    impl = String(512)
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        return validate_relative_key(value) if value is not None else None


class Digest(TypeDecorator[str]):
    impl = String(71)
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        if value is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
            raise ValueError("Expected canonical sha256:<64 lowercase hex characters>")
        return value


class SmallJSON(TypeDecorator[Any]):
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is not None:
            if not isinstance(value, (dict, list)):
                raise ValueError("Expected a metadata object or array")
            if len(json.dumps(value, allow_nan=False).encode("utf-8")) > 16384:
                raise ValueError("Large payloads belong in artifacts, not metadata")
        return value


class FileList(SmallJSON):
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if not isinstance(value, list) or not value or len(value) > 100:
            raise ValueError("Expected one to 100 changed files")
        for path in value:
            validate_relative_key(path)
        if len(value) != len(set(value)):
            raise ValueError("Changed files must be unique")
        return super().process_bind_param(value, dialect)
