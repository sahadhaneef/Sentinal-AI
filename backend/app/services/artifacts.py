"""Bounded, confined, integrity-checked reads of already-registered artifacts."""

import hashlib
from pathlib import Path

from app.core.config import Settings
from app.core.errors import ApiError
from app.core.logging import redact
from app.db.types import validate_relative_key
from app.models import Artifact
from app.repositories.unit_of_work import Store
from app.schemas.domain import ArtifactMetadata


def confined_path(root: Path, key: str) -> Path:
    """Reject traversal, symlinks and Windows junctions, including ancestor redirects."""
    try:
        validate_relative_key(key)
        current = root.absolute()
        for parent in [*reversed(current.parents), current]:
            if parent.is_symlink() or parent.is_junction():
                raise ValueError("Redirected root")
        target = current
        for part in key.split("/"):
            target /= part
            if target.is_symlink() or target.is_junction():
                raise ValueError("Redirected artifact")
        resolved = target.resolve(strict=True)
        resolved.relative_to(current.resolve(strict=True))
        return resolved
    except (OSError, ValueError):
        raise ApiError(
            503, "ARTIFACT_UNAVAILABLE", "The recorded artifact is unavailable."
        ) from None


class ArtifactReader:
    """Reads evidence only; never creates files, serves arbitrary paths or runs commands."""

    def __init__(self, store: Store, settings: Settings) -> None:
        self.store = store
        self.settings = settings

    def metadata(self, identity: str) -> ArtifactMetadata:
        artifact = self.store.records(Artifact).get(identity)
        return ArtifactMetadata.model_validate(artifact, from_attributes=True)

    def bytes_for_key(self, key: str) -> bytes:
        path = confined_path(self.settings.artifact_root, key)
        try:
            with path.open("rb") as source:
                data = source.read(self.settings.artifact_max_bytes + 1)
            if len(data) > self.settings.artifact_max_bytes:
                raise ValueError("Artifact exceeds projection bounds")
            return data
        except (OSError, ValueError):
            raise ApiError(
                503, "ARTIFACT_UNAVAILABLE", "The recorded artifact is unavailable."
            ) from None

    def text(self, identity: str, kinds: set[str]) -> str:
        artifact = self.store.records(Artifact).get(identity)
        if not artifact.redacted or artifact.kind not in kinds:
            raise ApiError(403, "FORBIDDEN", "This artifact cannot be exposed by this read view.")
        data = self.bytes_for_key(artifact.storage_key)
        if (
            len(data) != artifact.size_bytes
            or "sha256:" + hashlib.sha256(data).hexdigest() != artifact.sha256
        ):
            raise ApiError(503, "ARTIFACT_UNAVAILABLE", "Recorded artifact integrity check failed.")
        try:
            text = data.decode("utf-8")
            if redact(text) != text:
                raise ApiError(
                    403, "FORBIDDEN", "Artifact redaction must be reviewed before display."
                )
            return text
        except UnicodeDecodeError:
            raise ApiError(
                503, "ARTIFACT_UNAVAILABLE", "The recorded text is unavailable."
            ) from None
