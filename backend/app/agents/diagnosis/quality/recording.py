"""Explicit optional outcome audit using existing tables, without workflow mutation."""

from sqlalchemy import Engine

from app.models import AuditEvent, Incident, WorkflowRun
from app.repositories.unit_of_work import transaction

from .contracts import QualityResult


class OutcomeRecorder:
    """Caller authorizes audit persistence; default reasoning remains read-only."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def record(self, checked: QualityResult) -> str:
        """Persist hashes, IDs, retrieval ranks and review codes, never source/log bodies."""
        result = checked.result
        with transaction(self.engine) as store:
            incident = store.records(Incident).get(result.incident_id)
            run = store.records(WorkflowRun).get(result.run_id)
            scope = (result.application_id, result.input_revision)
            if (checked.provenance.application_id, checked.provenance.repository_revision) != scope:
                raise ValueError("Retrieval provenance does not match outcome scope")
            if (
                (incident.application_id, incident.repository_revision) != scope
                or (run.application_id, run.repository_revision) != scope
                or run.incident_id != incident.id
            ):
                raise ValueError("Outcome scope does not match the stored incident/run")
            event = store.records(AuditEvent).add(
                AuditEvent(
                    incident_id=incident.id,
                    application_id=result.application_id,
                    run_id=run.id,
                    event_type="diagnosis_quality_reviewed",
                    actor_type="agent",
                    actor_key="diagnosis",
                    payload_metadata={
                        "schema_version": "1.0",
                        "input_revision": result.input_revision,
                        "status": result.status,
                        "outcome": result.outcome,
                        "provider": result.provider,
                        "reason": result.error.code if result.error else "OK",
                        "retrieval": checked.provenance.model_dump(mode="json"),
                        "quality_codes": [issue.code for issue in checked.assessment.issues],
                    },
                )
            )
            return event.id
