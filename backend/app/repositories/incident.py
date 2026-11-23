"""Atomic incident persistence and deduplication without workflow dispatch."""

from sqlalchemy import select, text
from sqlalchemy.dialects.sqlite import insert

from app.models import Incident, IncidentMonitoringEvent, MonitoringEvent
from app.models.enums import INCIDENT_CLOSED, RunState
from app.models.incident import ACTIVE_INCIDENT_SQL
from app.repositories.base import Repository
from app.repositories.errors import Conflict
from app.schemas.monitoring import MonitoringInput as MonitoringInput


class IncidentRepository(Repository[Incident]):
    def record_monitoring_event(self, event: MonitoringInput) -> tuple[MonitoringEvent, Incident]:
        """Atomic DB deduplication only. No workflow dispatch or agent execution."""
        values = event.model_dump()
        self.session.execute(
            insert(MonitoringEvent)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["application_id", "source_event_id"])
        )
        stored = self.session.scalar(
            select(MonitoringEvent).where(
                MonitoringEvent.application_id == event.application_id,
                MonitoringEvent.source_event_id == event.source_event_id,
            )
        )
        if stored is None:
            raise Conflict("The monitoring event could not be recorded.")
        if any(getattr(stored, name) != value for name, value in values.items()):
            raise Conflict("The source event ID was reused for different evidence.")
        link = self.session.scalar(
            select(IncidentMonitoringEvent).where(
                IncidentMonitoringEvent.monitoring_event_id == stored.id
            )
        )
        if link is not None:
            return stored, self.get(link.incident_id)
        self.session.execute(
            insert(Incident)
            .values(
                application_id=event.application_id,
                repository_revision=event.repository_revision,
                source_event_id=event.source_event_id,
                fingerprint=event.fingerprint,
                severity=event.severity,
                error_type=event.error_type,
                message=event.message,
                status=RunState.DETECTED
                if event.classification == "supported"
                else RunState.MANUAL_REVIEW,
                current_stage="detected"
                if event.classification == "supported"
                else "manual_review",
                detected_at=event.occurred_at,
            )
            .on_conflict_do_nothing(
                index_elements=["application_id", "fingerprint"],
                index_where=text(ACTIVE_INCIDENT_SQL),
            )
        )
        incident = self.session.scalar(
            select(Incident).where(
                Incident.application_id == event.application_id,
                Incident.fingerprint == event.fingerprint,
                Incident.status.not_in(INCIDENT_CLOSED),
            )
        )
        if incident is None:
            raise Conflict("The incident could not be recorded.")
        if (
            incident.repository_revision != event.repository_revision
            or incident.error_type != event.error_type
        ):
            raise Conflict(
                "Active incident evidence belongs to a different source revision or error."
            )
        self.session.execute(
            insert(IncidentMonitoringEvent)
            .values(
                incident_id=incident.id,
                monitoring_event_id=stored.id,
                application_id=event.application_id,
                repository_revision=event.repository_revision,
            )
            .on_conflict_do_nothing(index_elements=["monitoring_event_id"])
        )
        return stored, incident
