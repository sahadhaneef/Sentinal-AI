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
from app.db.types import Token, UTCDateTime, utc_now
from app.models.application import Artifact
from app.models.common import Record, constraints
from app.models.enums import AgentStatus, AgentType, RunState, status_type
from app.models.incident import Incident


class WorkflowRun(Record, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["incident_id", "application_id", "repository_revision"],
            ["incidents.id", "incidents.application_id", "incidents.repository_revision"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "incident_id"),
        UniqueConstraint("id", "application_id", "repository_revision"),
        UniqueConstraint("incident_id", "attempt"),
        CheckConstraint("attempt >= 1", name="attempt_positive"),
        CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="run_time_order"),
        Index(
            "uq_workflow_runs_active_incident",
            "incident_id",
            unique=True,
            sqlite_where=text(
                "state NOT IN ('resolved','rejected','unresolved','reported',"
                "'manual_review','error')"
            ),
        ),
        Index(
            "uq_workflow_runs_applying_application",
            "application_id",
            unique=True,
            sqlite_where=text("state IN ('applying','verifying','restoring')"),
        ),
    )
    incident_id: Mapped[str] = mapped_column(String(64))
    application_id: Mapped[str] = mapped_column(String(64))
    repository_revision: Mapped[str] = mapped_column(Token())
    state: Mapped[RunState] = mapped_column(
        status_type(RunState, "run_state"), default=RunState.DETECTED
    )
    attempt: Mapped[int] = mapped_column(default=1)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    error_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    incident: Mapped[Incident] = relationship(viewonly=True)
    transitions: Mapped[list["StageTransition"]] = relationship(viewonly=True)
    executions: Mapped[list["AgentExecution"]] = relationship(viewonly=True)


class StageTransition(Record, Base):
    __tablename__ = "stage_transitions"
    __table_args__ = constraints(
        UniqueConstraint("run_id", "sequence"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        CheckConstraint("from_state IS NULL OR from_state != to_state", name="different_states"),
    )
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="RESTRICT"))
    sequence: Mapped[int] = mapped_column()
    from_state: Mapped[RunState | None] = mapped_column(status_type(RunState, "from_state"))
    to_state: Mapped[RunState] = mapped_column(status_type(RunState, "to_state"))
    reason: Mapped[str] = mapped_column(String(2000))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    run: Mapped[WorkflowRun] = relationship(viewonly=True)


class AgentExecution(Record, Base):
    __tablename__ = "agent_executions"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["run_id", "application_id", "input_revision"],
            [
                "workflow_runs.id",
                "workflow_runs.application_id",
                "workflow_runs.repository_revision",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("duration_ms >= 0", name="duration_nonnegative"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= created_at", name="execution_time_order"
        ),
        Index("ix_agent_executions_run_type", "run_id", "agent_type", "created_at"),
    )
    run_id: Mapped[str] = mapped_column(String(64))
    application_id: Mapped[str] = mapped_column(String(64))
    input_revision: Mapped[str] = mapped_column(Token())
    agent_type: Mapped[AgentType] = mapped_column(status_type(AgentType, "agent_type"))
    status: Mapped[AgentStatus] = mapped_column(
        status_type(AgentStatus, "agent_status"), default=AgentStatus.IDLE
    )
    stage: Mapped[str] = mapped_column(String(64))
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    duration_ms: Mapped[int] = mapped_column(default=0)
    output_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    error_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    run: Mapped[WorkflowRun] = relationship(viewonly=True)
    output: Mapped[Artifact | None] = relationship(foreign_keys=[output_artifact_id], viewonly=True)
