from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import Digest, FileList, Token, UTCDateTime, utc_now
from app.models.application import Artifact
from app.models.common import Record, constraints, digest_check
from app.models.enums import CheckStatus, PatchStatus, status_type
from app.models.identity import User
from app.models.workflow import WorkflowRun


class PatchCandidate(Record, Base):
    """Each revision is a new row/ID; the immutable diff is an artifact."""

    __tablename__ = "patch_candidates"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["run_id", "incident_id"],
            ["workflow_runs.id", "workflow_runs.incident_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["run_id", "application_id", "base_revision"],
            [
                "workflow_runs.id",
                "workflow_runs.application_id",
                "workflow_runs.repository_revision",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["supersedes_candidate_id", "incident_id"],
            ["patch_candidates.id", "patch_candidates.incident_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("incident_id", "version"),
        UniqueConstraint("id", "incident_id"),
        UniqueConstraint("id", "incident_id", "patch_hash", "base_revision"),
        UniqueConstraint("id", "patch_hash"),
        UniqueConstraint("id", "application_id"),
        digest_check("patch_hash"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "supersedes_candidate_id IS NULL OR supersedes_candidate_id != id",
            name="different_predecessor",
        ),
        Index("ix_patch_candidates_incident_version", "incident_id", "version"),
    )
    incident_id: Mapped[str] = mapped_column(String(64))
    run_id: Mapped[str] = mapped_column(String(64))
    application_id: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column()
    base_revision: Mapped[str] = mapped_column(Token())
    patch_hash: Mapped[str] = mapped_column(Digest())
    changed_files: Mapped[list[str]] = mapped_column(FileList())
    rationale: Mapped[str] = mapped_column(String(4000))
    diff_artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id", ondelete="RESTRICT"))
    status: Mapped[PatchStatus] = mapped_column(
        status_type(PatchStatus, "patch_status"), default=PatchStatus.PROPOSED
    )
    supersedes_candidate_id: Mapped[str | None] = mapped_column(String(64))
    run: Mapped[WorkflowRun] = relationship(foreign_keys=[run_id, incident_id], viewonly=True)
    diff_artifact: Mapped[Artifact] = relationship(viewonly=True)
    predecessor: Mapped["PatchCandidate | None"] = relationship(
        remote_side="PatchCandidate.id, PatchCandidate.incident_id", viewonly=True
    )
    validations: Mapped[list["ValidationResult"]] = relationship(viewonly=True)


class ValidationResult(Record, Base):
    __tablename__ = "validation_results"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["candidate_id", "patch_hash"],
            ["patch_candidates.id", "patch_candidates.patch_hash"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "candidate_id", "patch_hash", "status"),
        digest_check("patch_hash"),
        CheckConstraint("duration_ms >= 0", name="duration_nonnegative"),
        Index("ix_validation_results_candidate_created", "candidate_id", "created_at"),
    )
    candidate_id: Mapped[str] = mapped_column(String(64))
    patch_hash: Mapped[str] = mapped_column(Digest())
    status: Mapped[CheckStatus] = mapped_column(status_type(CheckStatus, "check_status"))
    environment_id: Mapped[str] = mapped_column(Token())
    evidence_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    duration_ms: Mapped[int] = mapped_column(default=0)
    candidate: Mapped[PatchCandidate] = relationship(viewonly=True)
    checks: Mapped[list["ValidationCheck"]] = relationship(viewonly=True)


class ValidationCheck(Record, Base):
    __tablename__ = "validation_checks"
    __table_args__ = constraints(
        UniqueConstraint("validation_id", "name"),
        CheckConstraint("duration_ms >= 0", name="duration_nonnegative"),
        CheckConstraint(
            "status != 'passed' OR (exit_code IS NOT NULL AND exit_code = 0)",
            name="passed_exit_zero",
        ),
    )
    validation_id: Mapped[str] = mapped_column(
        ForeignKey("validation_results.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[CheckStatus] = mapped_column(status_type(CheckStatus, "check_status"))
    exit_code: Mapped[int | None] = mapped_column()
    duration_ms: Mapped[int] = mapped_column(default=0)
    evidence_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    validation: Mapped[ValidationResult] = relationship(viewonly=True)


class ApprovalDecision(Record, Base):
    __tablename__ = "approval_decisions"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["candidate_id", "incident_id", "patch_hash", "base_revision"],
            [
                "patch_candidates.id",
                "patch_candidates.incident_id",
                "patch_candidates.patch_hash",
                "patch_candidates.base_revision",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["validation_id", "candidate_id", "patch_hash", "validation_status"],
            [
                "validation_results.id",
                "validation_results.candidate_id",
                "validation_results.patch_hash",
                "validation_results.status",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("candidate_id"),
        UniqueConstraint("id", "candidate_id", "patch_hash", "base_revision", "decision"),
        CheckConstraint("decision IN ('approve','reject')", name="decision"),
        CheckConstraint("length(comment) <= 2000", name="comment_length"),
        CheckConstraint(
            "(validation_id IS NULL AND validation_status IS NULL) OR "
            "(validation_id IS NOT NULL AND validation_status IS NOT NULL)",
            name="validation_pair",
        ),
        CheckConstraint(
            "decision != 'approve' OR (validation_id IS NOT NULL AND validation_status = 'passed')",
            name="approve_requires_passed_validation",
        ),
        digest_check("patch_hash"),
    )
    incident_id: Mapped[str] = mapped_column(String(64))
    candidate_id: Mapped[str] = mapped_column(String(64))
    patch_hash: Mapped[str] = mapped_column(Digest())
    base_revision: Mapped[str] = mapped_column(Token())
    decision: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    validation_id: Mapped[str | None] = mapped_column(String(64))
    validation_status: Mapped[CheckStatus | None] = mapped_column(
        status_type(CheckStatus, "validation_status")
    )
    comment: Mapped[str] = mapped_column(String(2000), default="")
    decided_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    candidate: Mapped[PatchCandidate] = relationship(viewonly=True)
    validation: Mapped[ValidationResult | None] = relationship(viewonly=True)
    actor: Mapped[User] = relationship(viewonly=True)
