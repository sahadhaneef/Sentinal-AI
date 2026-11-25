"""ORM-independent read boundaries; shared Manager field mappings remain unapproved.

Incident/run/log selection is one atomic context read so linkage checks cannot be
lost by decomposing it into unrelated fetches. Source resolution verifies the
snapshot, excerpt, hashes and exact citation together for the same reason.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from app.agents.diagnosis.code_rag.cache import VectorCache
from app.agents.diagnosis.code_rag.contracts import BoundSource, RetrievalRequest
from app.agents.diagnosis.reasoning.contracts import DiagnosisRequest
from app.agents.diagnosis.reasoning.repository import IncidentContext


@dataclass(frozen=True)
class RegisteredRevision:
    id: str
    application_id: str
    revision: str
    snapshot_artifact_id: str


@dataclass(frozen=True)
class IndexedSnapshot:
    manifest_ref: str
    members: list[dict[str, str]]


class ContextReader(Protocol):
    """Return sanitized incident observations after exact run/revision/log linkage checks."""

    def load(self, request: DiagnosisRequest) -> IncidentContext: ...


class RevisionReader(Protocol):
    def revision(self, application_id: str, revision: str) -> RegisteredRevision: ...


class SourceReader(RevisionReader, Protocol):
    def context(self, request: RetrievalRequest) -> None: ...
    def bind(self, application_id: str, revision: str) -> BoundSource: ...


class SnapshotReader(Protocol):
    """Resolve sealed snapshot bytes and citations, not mutable current worktree text."""

    def resolve(
        self, application_id: str, revision: str, manifest_ref: str, evidence_id: str
    ) -> dict[str, Any]: ...


class LogReader(Protocol):
    def stack_log(self, application_id: str, revision: str, artifact_id: str) -> str: ...


class EvidenceReader(SnapshotReader, LogReader, Protocol):
    """Combined snapshot/citation and scoped log artifact access."""


class CodeIndexReader(Protocol):
    def collection(self, key: str) -> IndexedSnapshot | None: ...
    def vectors(self, keys: list[str], dimensions: int) -> dict[str, list[float]]: ...


class StandaloneIndexReader:
    """Project existing persisted cache rows into detached value objects."""

    def __init__(self, cache: VectorCache) -> None:
        self.cache = cache

    def collection(self, key: str) -> IndexedSnapshot | None:
        value = self.cache.collection(key)
        return IndexedSnapshot(value.manifest_ref, value.members) if value is not None else None

    def vectors(self, keys: list[str], dimensions: int) -> dict[str, list[float]]:
        return self.cache.vectors(keys, dimensions)


@dataclass(frozen=True)
class RetrievalRepositories:
    """Inject read ports without changing the standalone persistent index writer."""

    source: SourceReader
    evidence: EvidenceReader
    index: CodeIndexReader
