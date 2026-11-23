"""Frozen frontend response projections and additive Phase 3 request contracts."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, field_validator

from app.db.types import validate_token
from app.models.enums import AgentStatus, AgentType, CheckStatus, PatchStatus, RunState, Severity
from app.schemas.common import WireModel
from app.schemas.monitoring import MonitoringInput


def record_identifier(value: str) -> str:
    """Keep path/query identifiers compatible with UUID and legacy opaque IDs."""
    return validate_token(value, 64)


Identifier = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"),
    AfterValidator(record_identifier),
]


class Application(WireModel):
    id: str
    name: str
    description: str
    workspace_key: str
    repository_revision: str
    monitoring_enabled: bool
    status: Literal["healthy", "degraded", "offline"]
    supported_errors: list[str]


class ApplicationRegistration(WireModel):
    """Only an operator-configured key; no client-owned filesystem paths."""

    workspace_key: str = Field(min_length=1, max_length=128)

    @field_validator("workspace_key")
    @classmethod
    def portable_key(cls, value: str) -> str:
        return validate_token(value)


class IncidentIngestion(MonitoringInput):
    """An authenticated operator's sanitized, normalized observation, not raw logs."""

    application_id: Identifier
    log_artifact_id: Identifier | None = None


class IncidentFilters(WireModel):
    status: RunState | None = None
    severity: Severity | None = None
    application_id: Identifier | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=2048)
    limit: int = Field(default=10, ge=1, le=100)
    search: str = Field(default="", max_length=200)
    scope: Literal["all", "open", "closed", "candidates", "pending"] = "all"
    sort: Literal["detected_desc", "detected_asc", "severity_desc"] = "detected_desc"


class Incident(WireModel):
    id: str
    application_id: str
    source_event_id: str
    fingerprint: str
    severity: Severity
    error_type: str
    message: str
    status: RunState
    current_stage: str
    repository_revision: str
    active_run_id: str | None
    detected_at: datetime
    resolved_at: datetime | None


class Page[T](WireModel):
    items: list[T]
    next_cursor: str | None
    total: int


class Evidence(WireModel):
    file_path: str
    symbol: str
    start_line: int
    end_line: int
    repository_revision: str
    artifact_id: str
    excerpt: str


class Diagnosis(WireModel):
    incident_id: str
    run_id: str
    status: Literal["completed", "manual_review"]
    hypothesis: str
    confidence_label: Literal["low", "medium", "high"]
    uncertainty: str
    suggested_direction: str
    evidence: list[Evidence]


class Patch(WireModel):
    id: str
    incident_id: str
    run_id: str
    version: int
    base_revision: str
    patch_hash: str
    changed_files: list[str]
    rationale: str
    diff_artifact_id: str
    status: PatchStatus
    diff: str


class Check(WireModel):
    name: str
    status: CheckStatus
    exit_code: int | None
    duration_ms: int
    evidence_artifact_id: str
    evidence: str


class Validation(WireModel):
    candidate_id: str
    patch_hash: str
    status: CheckStatus
    checks: list[Check]
    environment_id: str
    duration_ms: int


class Decision(WireModel):
    id: str
    incident_id: str
    candidate_id: str
    patch_hash: str
    base_revision: str
    decision: Literal["approve", "reject"]
    comment: str
    actor_id: str
    decided_at: datetime


class Attempt(WireModel):
    id: str
    candidate_id: str
    snapshot_ref: str
    before_revision: str
    after_revision: str | None
    status: Literal["applying", "verifying", "resolved", "unresolved"]
    applied_at: datetime
    restore_status: Literal["not_needed", "restored", "manual_action"]


class Verification(WireModel):
    id: str
    application_attempt_id: str
    candidate_id: str
    status: CheckStatus
    checks: list[Check]
    monitoring_observation: str
    evidence_artifact_id: str


class Report(WireModel):
    id: str
    incident_id: str
    version: int
    outcome: RunState
    report_artifact_id: str
    summary: str
    limitations: list[str]
    generated_at: datetime


class IncidentDetail(Incident):
    source_log: str
    diagnosis: Diagnosis | None
    patches: list[Patch]
    validation: Validation | None
    decision: Decision | None
    application_attempt: Attempt | None
    verification: Verification | None
    report: Report | None
    can_approve: bool = False
    can_reject: bool = False
    can_apply: bool = False
    permission_reason: str = (
        "Read-only backend phase. Decisions and application are not implemented."
    )


class Event(WireModel):
    id: str
    incident_id: str
    run_id: str
    event_type: str
    actor_type: Literal["agent", "human", "system"]
    actor_id: str
    payload: dict[str, Any]
    occurred_at: datetime


class Execution(WireModel):
    schema_version: Literal["1.0"] = "1.0"
    incident_id: str
    run_id: str
    stage: str
    agent_type: AgentType
    status: AgentStatus
    created_at: datetime
    input_revision: str
    error: str | None


class Agent(WireModel):
    agent_type: AgentType
    name: str
    status: AgentStatus
    responsibility: str
    owner: str
    current_task: str | None
    last_activity: datetime | None


class AgentDetail(Agent):
    inputs: list[str]
    outputs: list[str]
    recent_runs: list[Execution]


class Summary(WireModel):
    total_incidents: int
    open_incidents: int
    awaiting_approval: int
    resolved: int
    active_agents: int
    current_runs: int
    agent_statuses: list[Agent]
    last_updated: datetime


class SafeSettings(WireModel):
    monitoring_interval_seconds: int = Field(ge=3, le=60)
    max_candidate_revisions: int = Field(ge=0, le=2)


class DashboardOverview(WireModel):
    """Additive aggregates without changing the adapter's frozen summary shape."""

    summary: Summary
    registered_applications: int
    incidents_by_severity: dict[Severity, int]
    recent_activity: list[Event]
    recent_outcomes: list[Report]


class ArtifactMetadata(WireModel):
    """Public metadata never exposes a server storage key or absolute path."""

    id: str
    kind: str
    sha256: str
    content_type: str
    size_bytes: int
    redacted: bool


class Revision(WireModel):
    id: str
    revision: str
    snapshot_artifact_id: str
    indexed_at: datetime | None
    created_at: datetime


class ApplicationMetadata(WireModel):
    application: Application
    observation_status: Literal["not_observed", "recorded"]
    last_observed_at: datetime | None
    monitoring_worker_available: bool = False
    revisions: list[Revision]


class Run(WireModel):
    id: str
    incident_id: str
    state: RunState
    attempt: int
    started_at: datetime
    finished_at: datetime | None


class Transition(WireModel):
    sequence: int
    from_state: RunState | None
    to_state: RunState
    reason: str
    occurred_at: datetime


class RunDetail(Run):
    transitions: list[Transition]
