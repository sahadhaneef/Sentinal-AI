"""Internal retrieval DTOs extending existing evidence fields, not public diagnosis output."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from app.db.types import validate_token
from app.schemas.common import WireModel
from app.schemas.domain import Evidence, Identifier


@dataclass(frozen=True)
class BoundSource:
    """A catalog-validated scope; never include its private root in a public response."""

    application_id: str
    repository_revision: str
    registered_snapshot_ref: str
    root: Path = field(repr=False)


class SourceFile(WireModel):
    file_path: str
    language: str
    content: str = Field(repr=False)
    content_hash: str
    size_bytes: int


class IngestionReport(WireModel):
    files: list[SourceFile] = Field(repr=False)
    skipped: dict[str, int]
    total_bytes: int


class CodeChunk(WireModel):
    evidence_id: str
    application_id: str
    repository_revision: str
    file_path: str
    symbol: str
    start_line: int
    end_line: int
    content: str = Field(repr=False)
    content_hash: str
    language: str
    strategy: str


class RetrievalRequest(WireModel):
    """Manager-facing retrieval input; conclusions and workflow state belong to D2+."""

    schema_version: Literal["1.0"] = "1.0"
    application_id: Identifier
    repository_revision: str = Field(min_length=1, max_length=128)
    incident_id: Identifier | None = None
    run_id: Identifier | None = None
    error_type: str = Field(default="", max_length=200)
    error_message: str = Field(default="", max_length=2000, repr=False)
    stack_trace: str = Field(default="", max_length=16000, repr=False)
    stack_trace_ref: Identifier | None = None
    search_query: str = Field(default="", max_length=500, repr=False)
    top_k: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_query(self) -> "RetrievalRequest":
        validate_token(self.repository_revision)
        if self.run_id and not self.incident_id:
            raise ValueError("A run requires an incident identity")
        if (
            not any(
                value.strip()
                for value in (
                    self.error_type,
                    self.error_message,
                    self.stack_trace,
                    self.search_query,
                )
            )
            and not self.stack_trace_ref
        ):
            raise ValueError("Provide an incident query or a sanitized stack trace")
        return self


class RetrievedEvidence(Evidence):
    """An actual CodeIndexEntry and resolvable stored source range, not a hypothesis."""

    evidence_id: str
    application_id: str
    language: str
    content_hash: str
    source_snapshot_ref: str
    source_file_ref: str
    source_file_hash: str
    retrieval_method: Literal["semantic", "stack_line", "stack_symbol", "hybrid"]
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    semantic_score: float | None = Field(default=None, ge=-1, le=1, allow_inf_nan=False)
    exact_tier: int = Field(ge=0, le=2)


class RetrievalResult(WireModel):
    application_id: str
    repository_revision: str
    status: Literal["ready", "empty", "unavailable", "partial"]
    reason: str
    semantic_used: bool
    evidence: list[RetrievedEvidence]


class IndexReport(WireModel):
    application_id: str
    repository_revision: str
    source_snapshot_ref: str
    snapshot_hash: str
    files: int
    chunks: int
    embedded: int
    cached: int
    skipped: dict[str, int]
    provider_id: str
