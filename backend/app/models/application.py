from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import Digest, RelativeKey, SmallJSON, Token, UTCDateTime
from app.models.common import Record, constraints, digest_check, relative_check


class Artifact(Record, Base):
    __tablename__ = "artifacts"
    __table_args__ = constraints(
        digest_check("sha256"),
        relative_check("storage_key"),
        CheckConstraint("size_bytes >= 0", name="size_nonnegative"),
        CheckConstraint(
            "kind IN ('log','source_snapshot','source_excerpt','diff','test_output',"
            "'verification','report','diagnosis','snapshot')",
            name="artifact_kind",
        ),
    )
    kind: Mapped[str] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(RelativeKey(), unique=True)
    sha256: Mapped[str] = mapped_column(Digest())
    content_type: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column()
    redacted: Mapped[bool] = mapped_column(Boolean(create_constraint=True, name="redacted_bool"))


class Application(Record, Base):
    __tablename__ = "applications"
    __table_args__ = constraints(
        CheckConstraint("status IN ('healthy','degraded','offline')", name="application_status"),
        CheckConstraint("length(name) BETWEEN 1 AND 200", name="name_length"),
        CheckConstraint(
            "length(workspace_key) BETWEEN 1 AND 128 AND "
            "workspace_key NOT GLOB '*[^A-Za-z0-9_.-]*' AND "
            "instr(workspace_key,'..') = 0",
            name="workspace_key_format",
        ),
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(2000), default="")
    workspace_key: Mapped[str] = mapped_column(Token(), unique=True)
    monitoring_enabled: Mapped[bool] = mapped_column(
        Boolean(create_constraint=True, name="monitoring_bool"), default=False
    )
    status: Mapped[str] = mapped_column(String(16), default="offline")
    supported_errors: Mapped[list[str]] = mapped_column(SmallJSON(), default=list)
    revisions: Mapped[list["RepositoryRevision"]] = relationship(viewonly=True)
    revision_selection: Mapped["ApplicationRevision | None"] = relationship(viewonly=True)


class RepositoryRevision(Record, Base):
    __tablename__ = "repository_revisions"
    __table_args__ = constraints(
        UniqueConstraint("application_id", "revision"),
        UniqueConstraint("id", "application_id"),
        CheckConstraint(
            "length(revision) BETWEEN 1 AND 128 AND "
            "revision NOT GLOB '*[^A-Za-z0-9_.-]*' AND instr(revision,'..') = 0",
            name="revision_format",
        ),
    )
    application_id: Mapped[str] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"))
    revision: Mapped[str] = mapped_column(Token())
    snapshot_artifact_id: Mapped[str] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    indexed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    application: Mapped[Application] = relationship(viewonly=True)
    snapshot: Mapped[Artifact] = relationship(viewonly=True)


class ApplicationRevision(Record, Base):
    """One current revision selection without a circular application/revision FK."""

    __tablename__ = "application_revisions"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["revision_id", "application_id"],
            ["repository_revisions.id", "repository_revisions.application_id"],
            ondelete="RESTRICT",
        )
    )
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="RESTRICT"), unique=True
    )
    revision_id: Mapped[str] = mapped_column(String(64))
    revision: Mapped[RepositoryRevision] = relationship(viewonly=True)


class BackendSettings(Record, Base):
    __tablename__ = "backend_settings"
    __table_args__ = constraints(
        CheckConstraint("singleton_key = 'settings'", name="singleton_key"),
        CheckConstraint("monitoring_interval_seconds BETWEEN 3 AND 60", name="monitoring_interval"),
        CheckConstraint("max_candidate_revisions BETWEEN 0 AND 2", name="candidate_revisions"),
    )
    singleton_key: Mapped[str] = mapped_column(String(16), default="settings", unique=True)
    monitoring_interval_seconds: Mapped[int] = mapped_column(default=5)
    max_candidate_revisions: Mapped[int] = mapped_column(default=2)


class CodeIndexEntry(Record, Base):
    __tablename__ = "code_index_entries"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["application_id", "repository_revision"],
            ["repository_revisions.application_id", "repository_revisions.revision"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "application_id", "repository_revision", "file_path", "start_line", "end_line"
        ),
        UniqueConstraint("id", "application_id", "repository_revision"),
        digest_check("content_hash"),
        relative_check("file_path"),
        CheckConstraint("start_line >= 1 AND end_line >= start_line", name="line_range"),
    )
    application_id: Mapped[str] = mapped_column(String(64))
    repository_revision: Mapped[str] = mapped_column(Token())
    file_path: Mapped[str] = mapped_column(RelativeKey())
    symbol: Mapped[str] = mapped_column(String(300))
    start_line: Mapped[int] = mapped_column()
    end_line: Mapped[int] = mapped_column()
    content_hash: Mapped[str] = mapped_column(Digest())
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id", ondelete="RESTRICT"))
    index_metadata: Mapped[dict[str, Any]] = mapped_column(SmallJSON(), default=dict)
    artifact: Mapped[Artifact] = relationship(viewonly=True)
