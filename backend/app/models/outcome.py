from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import Digest, SmallJSON, Token, UTCDateTime, utc_now
from app.models.common import Record, constraints, digest_check
from app.models.enums import CheckStatus, RunState, status_type
from app.models.incident import Incident
from app.models.repair import ApprovalDecision, PatchCandidate


class ApplicationAttempt(Record, Base):
    """A persistence record only; this model never writes a patch to a workspace."""

    __tablename__ = "application_attempts"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["approval_id", "candidate_id", "patch_hash", "before_revision", "approval_decision"],
            [
                "approval_decisions.id",
                "approval_decisions.candidate_id",
                "approval_decisions.patch_hash",
                "approval_decisions.base_revision",
                "approval_decisions.decision",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["candidate_id", "application_id"],
            ["patch_candidates.id", "patch_candidates.application_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["application_id", "after_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "candidate_id"),
        UniqueConstraint("approval_id"),
        digest_check("patch_hash"),
        CheckConstraint("approval_decision = 'approve'", name="approved_decision_only"),
        CheckConstraint(
            "status IN ('applying','verifying','resolved','unresolved')", name="attempt_status"
        ),
        CheckConstraint(
            "restore_status IN ('not_needed','restored','manual_action')", name="restore_status"
        ),
        CheckConstraint(
            "status != 'resolved' OR after_revision IS NOT NULL", name="resolved_revision"
        ),
        Index(
            "uq_application_attempts_active_application",
            "application_id",
            unique=True,
            sqlite_where=text("status IN ('applying','verifying')"),
        ),
    )
    application_id: Mapped[str] = mapped_column(String(64))
    candidate_id: Mapped[str] = mapped_column(String(64))
    approval_id: Mapped[str] = mapped_column(String(64))
    approval_decision: Mapped[str] = mapped_column(String(8), default="approve")
    patch_hash: Mapped[str] = mapped_column(Digest())
    before_revision: Mapped[str] = mapped_column(Token())
    after_revision: Mapped[str | None] = mapped_column(Token())
    snapshot_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="applying")
    applied_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    restore_status: Mapped[str] = mapped_column(String(16), default="not_needed")
    approval: Mapped[ApprovalDecision] = relationship(viewonly=True)
    candidate: Mapped[PatchCandidate] = relationship(viewonly=True)
    verifications: Mapped[list["VerificationResult"]] = relationship(viewonly=True)


class VerificationResult(Record, Base):
    __tablename__ = "verification_results"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["application_attempt_id", "candidate_id"],
            ["application_attempts.id", "application_attempts.candidate_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("duration_ms >= 0", name="duration_nonnegative"),
        Index("ix_verification_results_attempt_created", "application_attempt_id", "created_at"),
    )
    application_attempt_id: Mapped[str] = mapped_column(String(64))
    candidate_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[CheckStatus] = mapped_column(status_type(CheckStatus, "check_status"))
    duration_ms: Mapped[int] = mapped_column(default=0)
    monitoring_observation: Mapped[str] = mapped_column(String(2000))
    evidence_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    attempt: Mapped[ApplicationAttempt] = relationship(viewonly=True)
    checks: Mapped[list["VerificationCheck"]] = relationship(viewonly=True)


class VerificationCheck(Record, Base):
    __tablename__ = "verification_checks"
    __table_args__ = constraints(
        UniqueConstraint("verification_id", "name"),
        CheckConstraint("duration_ms >= 0", name="duration_nonnegative"),
        CheckConstraint(
            "status != 'passed' OR (exit_code IS NOT NULL AND exit_code = 0)",
            name="passed_exit_zero",
        ),
    )
    verification_id: Mapped[str] = mapped_column(
        ForeignKey("verification_results.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[CheckStatus] = mapped_column(status_type(CheckStatus, "check_status"))
    exit_code: Mapped[int | None] = mapped_column()
    duration_ms: Mapped[int] = mapped_column(default=0)
    evidence_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    verification: Mapped[VerificationResult] = relationship(viewonly=True)


class IncidentReport(Record, Base):
    __tablename__ = "incident_reports"
    __table_args__ = constraints(
        UniqueConstraint("incident_id", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "outcome IN ('resolved','rejected','unresolved','manual_review','error','reported')",
            name="terminal_outcome",
        ),
        Index("ix_incident_reports_incident_generated", "incident_id", "generated_at"),
    )
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column()
    outcome: Mapped[RunState] = mapped_column(status_type(RunState, "run_state"))
    report_artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id", ondelete="RESTRICT"))
    summary: Mapped[str] = mapped_column(String(4000))
    limitations: Mapped[list[str]] = mapped_column(SmallJSON(), default=list)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    incident: Mapped[Incident] = relationship(viewonly=True)
