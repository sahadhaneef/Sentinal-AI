"""SQLAlchemy ORM models for all 15 database entities."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ?? Applications ?????????????????????????????????????????????????????????????

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    workspace_key: Mapped[str] = mapped_column(String, nullable=False)
    repository_revision: Mapped[str] = mapped_column(String, default="HEAD")
    monitoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="healthy")  # healthy|degraded|offline
    supported_errors: Mapped[str] = mapped_column(Text, default="[]")  # JSON list
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    incidents: Mapped[list[Incident]] = relationship(back_populates="application")


# ?? Incidents ?????????????????????????????????????????????????????????????????

class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_incident_fingerprint"),
        Index("ix_incidents_app_status_detected", "application_id", "status", "detected_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id"), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, default="medium")
    error_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_log: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="detected")
    current_stage: Mapped[str] = mapped_column(String, default="detected")
    repository_revision: Mapped[str] = mapped_column(String, default="HEAD")
    active_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    application: Mapped[Application] = relationship(back_populates="incidents")
    runs: Mapped[list[IncidentRun]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    events: Mapped[list[IncidentEvent]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    diagnoses: Mapped[list[Diagnosis]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    patch_candidates: Mapped[list[PatchCandidate]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    approval_decisions: Mapped[list[ApprovalDecision]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    reports: Mapped[list[IncidentReport]] = relationship(back_populates="incident", cascade="all, delete-orphan")


# ?? Incident Runs ?????????????????????????????????????????????????????????????

class IncidentRun(Base):
    __tablename__ = "incident_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    schema_version: Mapped[str] = mapped_column(String, default="1.0")
    state: Mapped[str] = mapped_column(String, default="detected")
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    started_at: Mapped[datetime] = mapped_column(default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="runs")
    agent_executions: Mapped[list[AgentExecution]] = relationship(back_populates="run", cascade="all, delete-orphan")


# ?? Agent Executions ??????????????????????????????????????????????????????????

class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("incident_runs.id"), nullable=False)
    agent_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="running")  # idle|running|completed|error|offline
    input_revision: Mapped[str] = mapped_column(String, default="HEAD")
    started_at: Mapped[datetime] = mapped_column(default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_artifact_id: Mapped[str | None] = mapped_column(String, nullable=True)

    run: Mapped[IncidentRun] = relationship(back_populates="agent_executions")


# ?? Incident Events (append-only audit) ???????????????????????????????????????

class IncidentEvent(Base):
    __tablename__ = "incident_events"
    __table_args__ = (
        Index("ix_events_incident_occurred", "incident_id", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_type: Mapped[str] = mapped_column(String, default="system")  # agent|human|system
    actor_id: Mapped[str] = mapped_column(String, default="system")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(default=_now)

    incident: Mapped[Incident] = relationship(back_populates="events")


# ?? Diagnoses ?????????????????????????????????????????????????????????????????

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, default="")
    confidence_label: Mapped[str] = mapped_column(String, default="low")
    uncertainty: Mapped[str] = mapped_column(Text, default="")
    suggested_direction: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String, default="completed")  # completed|manual_review
    created_at: Mapped[datetime] = mapped_column(default=_now)

    incident: Mapped[Incident] = relationship(back_populates="diagnoses")


# ?? Patch Candidates ??????????????????????????????????????????????????????????

class PatchCandidate(Base):
    __tablename__ = "patch_candidates"
    __table_args__ = (
        Index("ix_candidates_incident_version", "incident_id", "version"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    base_revision: Mapped[str] = mapped_column(String, nullable=False)
    patch_hash: Mapped[str] = mapped_column(String, nullable=False)
    diff_artifact_id: Mapped[str | None] = mapped_column(String, nullable=True)
    diff_content: Mapped[str] = mapped_column(Text, default="")
    changed_files_json: Mapped[str] = mapped_column(Text, default="[]")
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="proposed")  # proposed|validated|failed|stale|approved|rejected|applied
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)

    incident: Mapped[Incident] = relationship(back_populates="patch_candidates")
    validation_results: Mapped[list[ValidationResult]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    approval_decisions: Mapped[list[ApprovalDecision]] = relationship(back_populates="candidate")
    application_attempts: Mapped[list[ApplicationAttempt]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


# ?? Validation Results ????????????????????????????????????????????????????????

class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("patch_candidates.id"), nullable=False)
    patch_hash: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="not_run")  # passed|failed|error|timeout|not_run
    checks_json: Mapped[str] = mapped_column(Text, default="[]")
    environment_id: Mapped[str] = mapped_column(String, default="")
    evidence_artifact_id: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    candidate: Mapped[PatchCandidate] = relationship(back_populates="validation_results")


# ?? Approval Decisions ????????????????????????????????????????????????????????

class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("patch_candidates.id"), nullable=False)
    patch_hash: Mapped[str] = mapped_column(String, nullable=False)
    base_revision: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str] = mapped_column(String, nullable=False)  # approve|reject
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(default=_now)

    incident: Mapped[Incident] = relationship(back_populates="approval_decisions")
    candidate: Mapped[PatchCandidate] = relationship(back_populates="approval_decisions")


# ?? Application Attempts ??????????????????????????????????????????????????????

class ApplicationAttempt(Base):
    __tablename__ = "application_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("patch_candidates.id"), nullable=False)
    snapshot_ref: Mapped[str] = mapped_column(String, default="")
    before_revision: Mapped[str] = mapped_column(String, nullable=False)
    after_revision: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="applying")  # applying|verifying|resolved|unresolved
    applied_at: Mapped[datetime] = mapped_column(default=_now)
    restore_status: Mapped[str] = mapped_column(String, default="not_needed")  # not_needed|restored|manual_action

    candidate: Mapped[PatchCandidate] = relationship(back_populates="application_attempts")
    verification_results: Mapped[list[VerificationResult]] = relationship(back_populates="application_attempt", cascade="all, delete-orphan")


# ?? Verification Results ??????????????????????????????????????????????????????

class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    application_attempt_id: Mapped[str] = mapped_column(ForeignKey("application_attempts.id"), nullable=False)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="not_run")
    checks_json: Mapped[str] = mapped_column(Text, default="[]")
    monitoring_observation_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_artifact_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    application_attempt: Mapped[ApplicationAttempt] = relationship(back_populates="verification_results")


# ?? Incident Reports ??????????????????????????????????????????????????????????

class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    report_artifact_id: Mapped[str] = mapped_column(String, default="")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    generated_at: Mapped[datetime] = mapped_column(default=_now)

    incident: Mapped[Incident] = relationship(back_populates="reports")


# ?? Artifacts ?????????????????????????????????????????????????????????????????

class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(String, default="")
    content_type: Mapped[str] = mapped_column(String, default="text/plain")
    redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=_now)


# ?? Code Index Entries ????????????????????????????????????????????????????????

class CodeIndexEntry(Base):
    __tablename__ = "code_index_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    application_id: Mapped[str] = mapped_column(String, nullable=False)
    repository_revision: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, default="")
    start_line: Mapped[int] = mapped_column(Integer, default=1)
    end_line: Mapped[int] = mapped_column(Integer, default=1)
    content_hash: Mapped[str] = mapped_column(String, default="")
    index_ref: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(default=_now)


# ?? Settings ??????????????????????????????????????????????????????????????????

class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


# ?? Idempotency Records ???????????????????????????????????????????????????????

class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)
