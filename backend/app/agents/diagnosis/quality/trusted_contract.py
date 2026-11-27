"""Diagnosis-side D4C.1 verification primitives for Manager-owned inputs."""

from datetime import UTC, datetime
from hashlib import sha256
from math import isfinite
from time import monotonic
from typing import Protocol

from pydantic import AwareDatetime, ConfigDict, Field, field_validator

from app.agents.diagnosis.execution.worker import IsolatedDiagnosisWorker, WorkerOutcome
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.db.types import validate_token
from app.schemas.common import WireModel
from app.schemas.domain import Identifier


class InvocationContext(WireModel):
    """Immutable admission delivered by the Manager supervisor."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    execution_id: Identifier
    run_id: Identifier
    incident_id: Identifier
    application_id: Identifier
    repository_id: Identifier
    revision_id: Identifier
    repository_revision: str
    snapshot_id: Identifier
    attempt_number: int = Field(ge=1, strict=True)
    invocation_id: Identifier
    idempotency_key: str = Field(min_length=1, repr=False)
    deadline_at: AwareDatetime

    @field_validator("repository_revision")
    @classmethod
    def immutable_revision(cls, value: str) -> str:
        """Reject common moving aliases before checking authoritative registration."""
        validate_token(value)
        if value.casefold() in {"head", "main", "master", "develop", "latest"}:
            raise ValueError("An immutable registered revision is required")
        return value


class ManifestReadRequest(WireModel):
    """Registered coordinates supplied to the scoped reader."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    application_id: Identifier
    repository_id: Identifier
    revision_id: Identifier
    snapshot_id: Identifier


class RegisteredRevisionDTO(ManifestReadRequest):
    """Authoritative registration detached from the Manager session."""

    revision: str
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_artifact_id: Identifier


class ScopedArtifactReadRequest(WireModel):
    """Artifact scope authorized by Manager."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    application_id: Identifier
    incident_id: Identifier
    run_id: Identifier
    execution_id: Identifier
    revision_id: Identifier
    artifact_id: Identifier
    max_bytes: int = Field(gt=0, strict=True)


class ScopedArtifactReadResult(WireModel):
    """Detached bytes and metadata returned by a scoped reader."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    artifact_id: Identifier
    content_hash: str
    content_size: int = Field(ge=0, strict=True)
    content_bytes: bytes = Field(strict=True)


class ManifestReadResult(WireModel):
    """Detached manifest bytes and metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest_artifact_id: Identifier
    manifest_hash: str
    content_size: int = Field(ge=0, strict=True)
    content_bytes: bytes = Field(strict=True)


class RevisionReader(Protocol):
    """Resolve one authorized registration by immutable coordinates."""

    def resolve_registered_revision(self, request: ManifestReadRequest) -> RegisteredRevisionDTO:
        """Return the canonical registration or raise on invalid scope."""
        ...


class ManifestReader(Protocol):
    """Manager-owned scoped manifest access."""

    def read_registered_manifest(self, request: ManifestReadRequest) -> ManifestReadResult:
        """Return the immutable manifest or raise on denied access."""
        ...


class ArtifactReader(Protocol):
    """Manager-owned scoped artifact access."""

    def read_scoped_artifact(self, request: ScopedArtifactReadRequest) -> ScopedArtifactReadResult:
        """Return the authorized artifact or raise on denied access."""
        ...


def _verified_bytes(content: bytes, size: int, maximum: int, digest: str) -> bytes:
    if not 0 <= size == len(content) <= maximum:
        raise ValueError("Diagnosis content size mismatch")
    if sha256(content).hexdigest() != digest:
        raise ValueError("Diagnosis content digest mismatch")
    return content


def read_verified_manifest(
    context: InvocationContext,
    revisions: RevisionReader,
    reader: ManifestReader,
    *,
    max_bytes: int,
) -> bytes:
    """Verify exact stored bytes against independent registration metadata."""
    request = ManifestReadRequest(
        application_id=context.application_id,
        repository_id=context.repository_id,
        revision_id=context.revision_id,
        snapshot_id=context.snapshot_id,
    )
    record = revisions.resolve_registered_revision(request)
    if record.model_dump(include=set(ManifestReadRequest.model_fields)) != request.model_dump():
        raise ValueError("Diagnosis registration scope mismatch")
    if record.revision != context.repository_revision:
        raise ValueError("Diagnosis registration revision mismatch")
    result = reader.read_registered_manifest(request)
    if (
        result.manifest_artifact_id != record.manifest_artifact_id
        or result.manifest_hash != record.manifest_hash
    ):
        raise ValueError("Diagnosis manifest metadata mismatch")
    return _verified_bytes(
        result.content_bytes, result.content_size, max_bytes, record.manifest_hash
    )


def read_verified_artifact(
    context: InvocationContext,
    request: ScopedArtifactReadRequest,
    reader: ArtifactReader,
    *,
    expected_sha256: str,
) -> bytes:
    """Verify bytes against a digest supplied by trusted Manager metadata."""
    scope = set(ScopedArtifactReadRequest.model_fields) - {"artifact_id", "max_bytes"}
    if context.model_dump(include=scope) != request.model_dump(include=scope):
        raise ValueError("Diagnosis artifact scope mismatch")
    result = reader.read_scoped_artifact(request)
    if result.artifact_id != request.artifact_id or result.content_hash != expected_sha256:
        raise ValueError("Diagnosis artifact metadata mismatch")
    return _verified_bytes(
        result.content_bytes, result.content_size, request.max_bytes, expected_sha256
    )


class InvocationState(Protocol):
    """Read Manager's current admission state through a trusted boundary."""

    def is_current(self, context: InvocationContext) -> bool:
        """Check that the exact admission is active and eligible."""
        ...


class SupervisedInvocation:
    """Bind one worker call using an admission furnished by the trusted supervisor.

    This is an internal primitive. Manager must authenticate the admission and
    atomically accept results across supervisor objects.
    """

    def __init__(self, context: InvocationContext, state: InvocationState) -> None:
        self._admission = context.model_dump_json()
        self._state = state
        self._used = False

    def _check(self, context: InvocationContext, deadline: float) -> None:
        if (
            not isfinite(deadline)
            or monotonic() >= deadline
            or datetime.now(UTC) >= context.deadline_at
            or not self._state.is_current(context)
        ):
            raise ValueError("Diagnosis invocation is no longer active")

    async def run(
        self, worker: IsolatedDiagnosisWorker, *, deadline: float
    ) -> tuple[InvocationContext, WorkerOutcome]:
        """Run one attempt and return its local binding for Manager acceptance."""
        if self._used:
            raise ValueError("Diagnosis invocation already consumed")
        self._used = True
        context = InvocationContext.model_validate_json(self._admission)
        self._check(context, deadline)
        deadline = min(
            deadline, monotonic() + (context.deadline_at - datetime.now(UTC)).total_seconds()
        )
        request = DiagnosisRequest(
            incident_id=context.incident_id,
            run_id=context.run_id,
            application_id=context.application_id,
            repository_revision=context.repository_revision,
        )
        outcome = await worker.diagnose(request, deadline=deadline)
        self._check(context, deadline)
        if outcome.quality is not None:
            if (
                outcome.quality.audit_event_id is not None
                or outcome.quality.result.used_test_fallback
            ):
                raise ValueError("Integrated Diagnosis cannot persist audit or use test fallback")
            result = outcome.quality.result
            if (
                result.incident_id,
                result.run_id,
                result.application_id,
                result.input_revision,
            ) != (
                context.incident_id,
                context.run_id,
                context.application_id,
                context.repository_revision,
            ):
                raise ValueError("Diagnosis result scope mismatch")
        return context, outcome
