"""Deterministic content hashes and record identifiers for immutable citations."""

import hashlib
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5


def digest(data: bytes) -> str:
    """Use the project's canonical SHA-256 representation."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    """Encode metadata deterministically without interpreter hash randomization."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def identity(kind: str, *parts: Any) -> str:
    """Derive stable UUIDs from actual scope, location and content identity."""
    return str(uuid5(NAMESPACE_URL, canonical(["sentinel-code-rag-v1", kind, *parts]).decode()))
