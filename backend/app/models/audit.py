from datetime import datetime
from typing import Any

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
from app.db.types import Digest, SmallJSON, UTCDateTime, utc_now
from app.models.common import Record, constraints, digest_check
from app.models.incident import Incident


class AuditEvent(Record, Base):
    __tablename__ = "audit_events"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["incident_id", "application_id"],
            ["incidents.id", "incidents.application_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["run_id", "incident_id"],
            ["workflow_runs.id", "workflow_runs.incident_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("actor_type IN ('agent','human','system')", name="actor_type"),
        CheckConstraint("actor_type != 'human' OR actor_user_id IS NOT NULL", name="human_actor"),
        CheckConstraint("run_id IS NULL OR incident_id IS NOT NULL", name="run_requires_incident"),
        CheckConstraint(
            "incident_id IS NULL OR application_id IS NOT NULL",
            name="incident_requires_application",
        ),
        Index("ix_audit_events_incident_occurred", "incident_id", "occurred_at"),
        Index("ix_audit_events_application_occurred", "application_id", "occurred_at"),
    )
    incident_id: Mapped[str | None] = mapped_column(String(64))
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT")
    )
    run_id: Mapped[str | None] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(100))
    actor_type: Mapped[str] = mapped_column(String(16))
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    actor_key: Mapped[str] = mapped_column(String(128))
    payload_metadata: Mapped[dict[str, Any]] = mapped_column(SmallJSON(), default=dict)
    payload_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
    incident: Mapped[Incident | None] = relationship(viewonly=True)


class IdempotencyRecord(Record, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = constraints(
        digest_check("request_hash"),
        UniqueConstraint("actor_user_id", "operation", "key"),
        CheckConstraint("status IN ('pending','completed','failed')", name="idempotency_status"),
    )
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    operation: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(Digest())
    status: Mapped[str] = mapped_column(String(16), default="pending")
    response_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
