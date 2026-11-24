"""Read existing incident/run/log context without creating executions or diagnoses."""

from dataclasses import dataclass

from sqlalchemy import Engine, select

from app.core.config import Settings
from app.core.logging import redact
from app.models import Incident, IncidentMonitoringEvent, MonitoringEvent, WorkflowRun
from app.repositories.unit_of_work import transaction
from app.services.artifacts import ArtifactReader

from .contracts import DiagnosisRequest


class ContextRejected(Exception):
    """A safe stable reason code, never a raw log or database failure."""


@dataclass(frozen=True)
class IncidentContext:
    error_type: str
    error_message: str
    stack_trace: str


class DiagnosisContextRepository:
    """Enforce exact incident/run/application/revision linkage before any LLM call."""

    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine, self.settings = engine, settings

    def load(self, request: DiagnosisRequest) -> IncidentContext:
        with transaction(self.engine) as store:
            incident = store.records(Incident).get(request.incident_id)
            run = store.records(WorkflowRun).get(request.run_id)
            scope = (request.application_id, request.repository_revision)
            if (
                (incident.application_id, incident.repository_revision) != scope
                or (run.application_id, run.repository_revision) != scope
                or run.incident_id != incident.id
            ):
                raise ContextRejected("CONTEXT_SCOPE_MISMATCH")
            error_type, message = redact(incident.error_type), redact(incident.message)
            if (request.error_type and request.error_type != error_type) or (
                request.error_message and request.error_message != message
            ):
                raise ContextRejected("INCIDENT_INPUT_CONFLICT")
            log_id = request.stack_trace_ref
            linked_logs = list(
                store.session.scalars(
                    select(MonitoringEvent.log_artifact_id)
                    .join(
                        IncidentMonitoringEvent,
                        IncidentMonitoringEvent.monitoring_event_id == MonitoringEvent.id,
                    )
                    .where(
                        IncidentMonitoringEvent.incident_id == incident.id,
                        MonitoringEvent.log_artifact_id.is_not(None),
                    )
                    .order_by(MonitoringEvent.id)
                    .limit(21)
                )
            )
            if log_id and log_id not in linked_logs:
                raise ContextRejected("LOG_SCOPE_MISMATCH")
            if not log_id and not request.stack_trace and linked_logs:
                log_id = linked_logs[0]
            trace = request.stack_trace
            if log_id:
                log = ArtifactReader(store, self.settings).text(log_id, {"log"})
                if len(log) > 16000 or "\x00" in log:
                    raise ContextRejected("MALFORMED_LOG")
                trace = "\n".join(value for value in (trace, log) if value)
            if len(trace) > 16000:
                raise ContextRejected("MALFORMED_LOG")
            return IncidentContext(error_type, message, redact(trace))
