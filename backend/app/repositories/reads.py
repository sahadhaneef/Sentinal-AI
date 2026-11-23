"""SQLAlchemy read queries shared by the Phase 3 application services."""

from typing import Any

from sqlalchemy import case, func, literal, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import AgentExecution, Application, Incident, PatchCandidate, WorkflowRun
from app.models.enums import INCIDENT_CLOSED, RUN_TERMINAL
from app.schemas.domain import IncidentFilters


class ReadRepository:
    """Keep persistence queries outside routes and projection/business services."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def find[T: Base](self, model: type[T], **matches: Any) -> list[T]:
        statement = select(model)
        for field, value in matches.items():
            statement = statement.where(getattr(model, field) == value)
        return list(self.session.scalars(statement.order_by(model.created_at, model.id)))

    def incident_rows(self, filters: IncidentFilters) -> list[Incident]:
        statement = select(Incident)
        for field in ("status", "severity", "application_id"):
            value = getattr(filters, field)
            if value is not None:
                statement = statement.where(getattr(Incident, field) == value)
        if filters.scope in {"open", "closed"}:
            closed = Incident.status.in_(INCIDENT_CLOSED)
            statement = statement.where(closed if filters.scope == "closed" else ~closed)
        if filters.scope in {"candidates", "pending"}:
            statement = statement.where(
                select(PatchCandidate.id).where(PatchCandidate.incident_id == Incident.id).exists()
            )
        if filters.scope == "pending":
            statement = statement.where(
                Incident.status.in_(
                    ["awaiting_approval", "approved", "applying", "verifying", "restoring"]
                )
            )
        if filters.search:
            searchable = (
                Incident.id + literal(" ") + Incident.error_type + literal(" ") + Incident.message
            )
            statement = statement.where(
                func.instr(func.casefold(searchable), filters.search.casefold()) > 0
            )
        ordering = []
        if filters.sort == "severity_desc":
            ordering.append(
                case(
                    {"critical": 4, "high": 3, "medium": 2, "low": 1}, value=Incident.severity
                ).desc()
            )
        ordering.extend(
            [
                Incident.detected_at.asc()
                if filters.sort == "detected_asc"
                else Incident.detected_at.desc(),
                Incident.id.asc(),
            ]
        )
        return list(self.session.scalars(statement.order_by(*ordering)))

    def incident_counts(self) -> dict[str, int]:
        statement = select(
            func.count(Incident.id),
            func.count(Incident.id).filter(Incident.status.not_in(INCIDENT_CLOSED)),
            func.count(Incident.id).filter(Incident.status == "awaiting_approval"),
            func.count(Incident.id).filter(Incident.status == "resolved"),
        )
        values = self.session.execute(statement).one()
        return dict(
            zip(
                ("total_incidents", "open_incidents", "awaiting_approval", "resolved"),
                values,
                strict=True,
            )
        )

    def active_run_count(self) -> int:
        return (
            self.session.scalar(
                select(func.count(WorkflowRun.id)).where(WorkflowRun.state.not_in(RUN_TERMINAL))
            )
            or 0
        )

    def agent_history(self, agent_type: str) -> list[AgentExecution]:
        return list(
            self.session.scalars(
                select(AgentExecution)
                .where(AgentExecution.agent_type == agent_type)
                .order_by(AgentExecution.created_at.desc(), AgentExecution.id.desc())
            )
        )

    def application_count(self) -> int:
        return self.session.scalar(select(func.count(Application.id))) or 0

    def severity_counts(self) -> dict[str, int]:
        return dict(
            self.session.execute(
                select(Incident.severity, func.count(Incident.id)).group_by(Incident.severity)
            ).all()
        )
