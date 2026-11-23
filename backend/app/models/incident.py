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
from app.db.types import Digest, Token, UTCDateTime, utc_now
from app.models.application import Application, Artifact, RepositoryRevision
from app.models.common import Record, constraints, digest_check
from app.models.enums import RunState, Severity, status_type

ACTIVE_INCIDENT_SQL = "status NOT IN ('resolved','rejected','unresolved','reported')"


class MonitoringEvent(Record, Base):
    __tablename__ = "monitoring_events"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["application_id", "repository_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("application_id", "source_event_id"),
        UniqueConstraint("id", "application_id", "repository_revision"),
        digest_check("fingerprint"),
        CheckConstraint("length(source_event_id) BETWEEN 1 AND 256", name="source_event_id_length"),
        CheckConstraint("length(message) BETWEEN 1 AND 2000", name="message_length"),
        CheckConstraint("classification IN ('supported','unsupported')", name="classification"),
        Index("ix_monitoring_events_application_fingerprint", "application_id", "fingerprint"),
    )
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"))
    repository_revision: Mapped[str] = mapped_column(Token())
    source_event_id: Mapped[str] = mapped_column(String(256))
    fingerprint: Mapped[str] = mapped_column(Digest())
    severity: Mapped[Severity] = mapped_column(status_type(Severity, "severity"))
    error_type: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(2000))
    classification: Mapped[str] = mapped_column(String(16), default="supported")
    log_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    application: Mapped[Application] = relationship(viewonly=True)
    log_artifact: Mapped[Artifact | None] = relationship(viewonly=True)


class Incident(Record, Base):
    __tablename__ = "incidents"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["application_id", "repository_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["application_id", "source_event_id"],
            ["monitoring_events.application_id", "monitoring_events.source_event_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id", "application_id"),
        UniqueConstraint("id", "application_id", "repository_revision"),
        digest_check("fingerprint"),
        CheckConstraint("length(message) BETWEEN 1 AND 2000", name="message_length"),
        CheckConstraint(
            "resolved_at IS NULL OR status IN ('resolved','reported')", name="resolved_status"
        ),
        Index(
            "uq_incidents_active_fingerprint",
            "application_id",
            "fingerprint",
            unique=True,
            sqlite_where=text(ACTIVE_INCIDENT_SQL),
        ),
        Index(
            "ix_incidents_application_status_detected", "application_id", "status", "detected_at"
        ),
    )
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"))
    repository_revision: Mapped[str] = mapped_column(Token())
    source_event_id: Mapped[str] = mapped_column(String(256))
    fingerprint: Mapped[str] = mapped_column(Digest())
    severity: Mapped[Severity] = mapped_column(status_type(Severity, "severity"))
    error_type: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(2000))
    status: Mapped[RunState] = mapped_column(
        status_type(RunState, "run_state"), default=RunState.DETECTED
    )
    current_stage: Mapped[str] = mapped_column(String(64), default="detected")
    detected_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    application: Mapped[Application] = relationship(viewonly=True)
    revision: Mapped[RepositoryRevision] = relationship(viewonly=True)
    monitoring_events: Mapped[list[MonitoringEvent]] = relationship(
        secondary="incident_monitoring_events", viewonly=True
    )
    runs: Mapped[list["WorkflowRun"]] = relationship(viewonly=True)  # noqa: F821


class IncidentMonitoringEvent(Record, Base):
    __tablename__ = "incident_monitoring_events"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["incident_id", "application_id", "repository_revision"],
            ["incidents.id", "incidents.application_id", "incidents.repository_revision"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["monitoring_event_id", "application_id", "repository_revision"],
            [
                "monitoring_events.id",
                "monitoring_events.application_id",
                "monitoring_events.repository_revision",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("monitoring_event_id"),
        Index("ix_incident_monitoring_events_incident", "incident_id"),
    )
    incident_id: Mapped[str] = mapped_column(String(64))
    monitoring_event_id: Mapped[str] = mapped_column(String(64))
    application_id: Mapped[str] = mapped_column(String(64))
    repository_revision: Mapped[str] = mapped_column(Token())
