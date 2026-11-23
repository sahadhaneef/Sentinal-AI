from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import Token
from app.models.application import CodeIndexEntry
from app.models.common import Record, constraints
from app.models.workflow import WorkflowRun


class Diagnosis(Record, Base):
    __tablename__ = "diagnoses"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["run_id", "application_id", "repository_revision"],
            [
                "workflow_runs.id",
                "workflow_runs.application_id",
                "workflow_runs.repository_revision",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("run_id"),
        UniqueConstraint("id", "application_id", "repository_revision"),
        CheckConstraint("status IN ('completed','manual_review')", name="diagnosis_status"),
        CheckConstraint("confidence_label IN ('low','medium','high')", name="confidence_label"),
    )
    run_id: Mapped[str] = mapped_column(String(64))
    application_id: Mapped[str] = mapped_column(String(64))
    repository_revision: Mapped[str] = mapped_column(Token())
    status: Mapped[str] = mapped_column(String(16))
    hypothesis: Mapped[str] = mapped_column(String(4000))
    confidence_label: Mapped[str] = mapped_column(String(8))
    uncertainty: Mapped[str] = mapped_column(String(2000))
    suggested_direction: Mapped[str] = mapped_column(String(2000))
    result_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="RESTRICT")
    )
    run: Mapped[WorkflowRun] = relationship(viewonly=True)
    evidence: Mapped[list["EvidenceReference"]] = relationship(viewonly=True)


class EvidenceReference(Record, Base):
    __tablename__ = "evidence_references"
    __table_args__ = constraints(
        ForeignKeyConstraint(
            ["diagnosis_id", "application_id", "repository_revision"],
            ["diagnoses.id", "diagnoses.application_id", "diagnoses.repository_revision"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["code_index_entry_id", "application_id", "repository_revision"],
            [
                "code_index_entries.id",
                "code_index_entries.application_id",
                "code_index_entries.repository_revision",
            ],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("diagnosis_id", "code_index_entry_id"),
    )
    diagnosis_id: Mapped[str] = mapped_column(String(64))
    code_index_entry_id: Mapped[str] = mapped_column(String(64))
    application_id: Mapped[str] = mapped_column(String(64))
    repository_revision: Mapped[str] = mapped_column(Token())
    source: Mapped[CodeIndexEntry] = relationship(viewonly=True)
    diagnosis: Mapped[Diagnosis] = relationship(viewonly=True)
