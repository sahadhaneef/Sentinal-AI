"""Database-backed frontend projections; no orchestration or mutation logic."""

from typing import Any

from pydantic import BaseModel

from app import models as models
from app.core.config import Settings
from app.core.errors import ApiError
from app.db.types import utc_now
from app.models.enums import RUN_TERMINAL, AgentType, Severity
from app.repositories.errors import NotFound
from app.repositories.reads import ReadRepository
from app.repositories.unit_of_work import Store
from app.schemas import domain as schemas
from app.services.artifacts import ArtifactReader
from app.services.cursors import CursorCodec, digest_json

AGENT_DEFINITIONS = {
    AgentType.MANAGER: (
        "Manager Agent",
        "Coordinates stage handoffs and human gates.",
        "Delvin",
        ["Incident", "Stage outcomes"],
        ["Workflow state", "Audit history"],
    ),
    AgentType.MONITORING: (
        "Monitoring Agent",
        "Records supported application observations.",
        "Neha",
        ["Sanitized sample logs"],
        ["Monitoring events", "Incidents"],
    ),
    AgentType.DIAGNOSIS: (
        "Diagnosis Agent",
        "Explains likely causes using revision-bound evidence.",
        "Sahad",
        ["Incident", "Source evidence"],
        ["Diagnosis", "Citations"],
    ),
    AgentType.REPAIR: (
        "Repair Agent",
        "Proposes focused, reviewable candidate changes.",
        "Yadhulakshmi",
        ["Diagnosis", "Source revision"],
        ["Candidate metadata", "Diff artifact"],
    ),
    AgentType.TESTING: (
        "Testing Agent",
        "Records isolated validation and post-application evidence.",
        "Sravan",
        ["Candidate", "Application attempt"],
        ["Validation", "Verification"],
    ),
    AgentType.REPORTING: (
        "Reporting Agent",
        "Records outcomes and their limitations.",
        "Neha",
        ["Persisted incident history"],
        ["Outcome report"],
    ),
}


def project[T: BaseModel](schema: type[T], record: Any, **overrides: Any) -> T:
    """Select only explicit response fields; never serialize an ORM row wholesale."""
    values = {
        field: getattr(record, field) for field in schema.model_fields if field not in overrides
    }
    return schema.model_validate(values | overrides)


class ReadService:
    """Coordinate repositories and safe projections for one request transaction."""

    def __init__(self, store: Store, settings: Settings, cursors: CursorCodec) -> None:
        self.store = store
        self.reads = ReadRepository(store.session)
        self.artifacts = ArtifactReader(store, settings)
        self.cursors = cursors

    def application(self, record: models.Application) -> schemas.Application:
        selection = record.revision_selection
        return project(
            schemas.Application,
            record,
            repository_revision=selection.revision.revision if selection else "",
            # Registration is not observation; do not infer health from an unobserved row.
            status=record.status
            if self.reads.find(models.MonitoringEvent, application_id=record.id)
            else "offline",
        )

    def applications(self) -> list[schemas.Application]:
        return [self.application(row) for row in self.reads.find(models.Application)]

    def application_metadata(self, identity: str) -> schemas.ApplicationMetadata:
        record = self.store.applications.get(identity)
        observations = self.reads.find(models.MonitoringEvent, application_id=identity)
        return schemas.ApplicationMetadata(
            application=self.application(record),
            observation_status="recorded" if observations else "not_observed",
            last_observed_at=max((row.occurred_at for row in observations), default=None),
            revisions=[project(schemas.Revision, row) for row in record.revisions],
        )

    def incident(self, row: models.Incident) -> schemas.Incident:
        active = [run for run in row.runs if run.state not in RUN_TERMINAL]
        if row.status == "resolved":
            self.require_recovery_evidence(row.id)
        return project(schemas.Incident, row, active_run_id=active[0].id if active else None)

    def incidents(self, filters: schemas.IncidentFilters) -> schemas.Page[schemas.Incident]:
        rows = self.reads.incident_rows(filters)
        query = digest_json(filters.model_dump(exclude={"cursor"}, mode="json"))
        snapshot = digest_json(
            [
                (
                    row.id,
                    row.updated_at,
                    row.status,
                    row.severity,
                    row.detected_at,
                    row.message,
                    row.error_type,
                )
                for row in rows
            ]
        )
        start = 0
        if filters.cursor:
            anchor = self.cursors.decode(filters.cursor, query, snapshot)
            positions = {row.id: index for index, row in enumerate(rows)}
            if anchor not in positions:
                raise ApiError(422, "VALIDATION_ERROR", "This cursor is stale. Restart pagination.")
            start = positions[anchor] + 1
        page = rows[start : start + filters.limit]
        cursor = None
        if page and start + len(page) < len(rows):
            cursor = self.cursors.encode(query, snapshot, page[-1].id)
        return schemas.Page(
            items=[self.incident(row) for row in page], next_cursor=cursor, total=len(rows)
        )

    def checks(self, rows: list[Any]) -> list[schemas.Check]:
        return [
            project(
                schemas.Check,
                row,
                evidence=self.artifacts.text(
                    row.evidence_artifact_id, {"test_output", "verification"}
                ),
            )
            for row in sorted(rows, key=lambda row: (row.name, row.id))
        ]

    def validation(self, candidate_id: str) -> schemas.Validation:
        candidate = self.store.patches.get(candidate_id)
        if not candidate.validations:
            raise NotFound("Validation has not been recorded.")
        latest = max(candidate.validations, key=lambda row: (row.created_at, row.id))
        checks = self.checks(latest.checks)
        if latest.status == "passed" and not self.passed(checks):
            raise ApiError(
                409, "EVIDENCE_INCOMPLETE", "Recorded validation lacks complete passed checks."
            )
        return project(schemas.Validation, latest, checks=checks)

    @staticmethod
    def passed(checks: list[Any]) -> bool:
        return bool(checks) and all(
            check.status == "passed" and check.exit_code == 0 for check in checks
        )

    def patch(self, row: models.PatchCandidate) -> schemas.Patch:
        return project(schemas.Patch, row, diff=self.artifacts.text(row.diff_artifact_id, {"diff"}))

    def patches(self, incident_id: str) -> list[schemas.Patch]:
        self.store.incidents.get(incident_id)
        rows = sorted(
            self.reads.find(models.PatchCandidate, incident_id=incident_id),
            key=lambda row: row.version,
        )
        return [self.patch(row) for row in rows]

    def diagnosis(self, incident_id: str) -> schemas.Diagnosis:
        incident = self.store.incidents.get(incident_id)
        rows = [
            row for run in incident.runs for row in self.reads.find(models.Diagnosis, run_id=run.id)
        ]
        if not rows:
            raise NotFound("Diagnosis has not been recorded.")
        row = max(rows, key=lambda item: (item.run.attempt, item.created_at, item.id))
        evidence = [
            project(
                schemas.Evidence,
                reference.source,
                excerpt=self.artifacts.text(reference.source.artifact_id, {"source_excerpt"}),
            )
            for reference in row.evidence
        ]
        return project(schemas.Diagnosis, row, incident_id=incident_id, evidence=evidence)

    def verification(self, row: models.VerificationResult) -> schemas.Verification:
        return project(schemas.Verification, row, checks=self.checks(row.checks))

    def latest_verification(self, incident_id: str) -> schemas.Verification:
        """Read the latest candidate's verification without unrelated log/diff I/O."""
        self.store.incidents.get(incident_id)
        candidates = self.reads.find(models.PatchCandidate, incident_id=incident_id)
        if candidates:
            candidate = max(candidates, key=lambda row: row.version)
            attempts = self.reads.find(models.ApplicationAttempt, candidate_id=candidate.id)
            if attempts:
                results = self.reads.find(
                    models.VerificationResult, application_attempt_id=attempts[-1].id
                )
                if results:
                    return self.verification(results[-1])
        raise NotFound("Verification has not been recorded.")

    def require_recovery_evidence(self, incident_id: str) -> None:
        attempts = [
            attempt
            for candidate in self.reads.find(models.PatchCandidate, incident_id=incident_id)
            for attempt in self.reads.find(models.ApplicationAttempt, candidate_id=candidate.id)
        ]
        for attempt in attempts:
            if attempt.status != "resolved" or not attempt.after_revision:
                continue
            for result in attempt.verifications:
                if result.status == "passed" and self.passed(result.checks):
                    self.artifacts.text(result.evidence_artifact_id, {"verification"})
                    self.checks(result.checks)
                    return
        raise ApiError(
            409, "EVIDENCE_INCOMPLETE", "Recorded recovery lacks passed verification evidence."
        )

    def report(self, row: models.IncidentReport) -> schemas.Report:
        if row.outcome == "resolved":
            self.require_recovery_evidence(row.incident_id)
        return project(schemas.Report, row)

    def reports(self, incident_id: str | None = None) -> list[schemas.Report]:
        if incident_id is not None:
            self.store.incidents.get(incident_id)
        rows = self.reads.find(
            models.IncidentReport, **({"incident_id": incident_id} if incident_id else {})
        )
        return [
            self.report(row)
            for row in sorted(rows, key=lambda row: (row.generated_at, row.version, row.id))
        ]

    def incident_detail(self, identity: str) -> schemas.IncidentDetail:
        row = self.store.incidents.get(identity)
        patches = self.patches(identity)
        candidate = patches[-1] if patches else None
        validations = (
            self.reads.find(models.ValidationResult, candidate_id=candidate.id) if candidate else []
        )
        decisions = (
            self.reads.find(models.ApprovalDecision, candidate_id=candidate.id) if candidate else []
        )
        attempts = (
            self.reads.find(models.ApplicationAttempt, candidate_id=candidate.id)
            if candidate
            else []
        )
        attempt = attempts[-1] if attempts else None
        verifications = (
            self.reads.find(models.VerificationResult, application_attempt_id=attempt.id)
            if attempt
            else []
        )
        diagnoses = [
            item for run in row.runs for item in self.reads.find(models.Diagnosis, run_id=run.id)
        ]
        events = self.reads.find(
            models.MonitoringEvent,
            application_id=row.application_id,
            source_event_id=row.source_event_id,
        )
        log_id = events[0].log_artifact_id if events else None
        reports = self.reports(identity)
        return schemas.IncidentDetail(
            **self.incident(row).model_dump(),
            source_log=self.artifacts.text(log_id, {"log"}) if log_id else "",
            diagnosis=self.diagnosis(identity) if diagnoses else None,
            patches=patches,
            validation=self.validation(candidate.id) if validations and candidate else None,
            decision=project(schemas.Decision, decisions[-1]) if decisions else None,
            application_attempt=project(
                schemas.Attempt, attempt, snapshot_ref=attempt.snapshot_artifact_id
            )
            if attempt
            else None,
            verification=self.verification(verifications[-1]) if verifications else None,
            report=reports[-1] if reports else None,
        )

    def events(self, incident_id: str) -> list[schemas.Event]:
        self.store.incidents.get(incident_id)
        rows = self.reads.find(models.AuditEvent, incident_id=incident_id)
        return [
            project(
                schemas.Event,
                row,
                run_id=row.run_id or "",
                actor_id=row.actor_key,
                payload=row.payload_metadata,
            )
            for row in sorted(rows, key=lambda row: (row.occurred_at, row.id))
        ]

    def runs(self, incident_id: str) -> list[schemas.RunDetail]:
        self.store.incidents.get(incident_id)
        return [
            project(
                schemas.RunDetail,
                row,
                transitions=[
                    project(schemas.Transition, item)
                    for item in sorted(row.transitions, key=lambda item: item.sequence)
                ],
            )
            for row in sorted(
                self.reads.find(models.WorkflowRun, incident_id=incident_id),
                key=lambda row: row.attempt,
            )
        ]

    def agent_summary(
        self,
        agent_type: AgentType,
        history: list[models.AgentExecution] | None = None,
    ) -> schemas.Agent:
        """Status metadata remains readable even when historical text is unavailable."""
        name, responsibility, owner, _, _ = AGENT_DEFINITIONS[agent_type]
        rows = history if history is not None else self.reads.agent_history(agent_type)
        latest = rows[0] if rows else None
        return schemas.Agent(
            agent_type=agent_type,
            name=name,
            responsibility=responsibility,
            owner=owner,
            status=latest.status if latest else "idle",
            current_task=latest.stage if latest and latest.status == "running" else None,
            last_activity=(latest.completed_at or latest.created_at) if latest else None,
        )

    def agent(self, agent_type: AgentType) -> schemas.AgentDetail:
        _, _, _, inputs, outputs = AGENT_DEFINITIONS[agent_type]
        rows = self.reads.agent_history(agent_type)
        return schemas.AgentDetail(
            **self.agent_summary(agent_type, rows).model_dump(),
            inputs=inputs,
            outputs=outputs,
            recent_runs=[
                project(
                    schemas.Execution,
                    row,
                    incident_id=row.run.incident_id,
                    error=self.artifacts.text(
                        row.error_artifact_id, {"log", "diagnosis", "test_output"}
                    )
                    if row.error_artifact_id
                    else None,
                )
                for row in rows[:100]
            ],
        )

    def agents(self) -> list[schemas.Agent]:
        return [self.agent_summary(kind) for kind in AgentType]

    def summary(self) -> schemas.Summary:
        agents = self.agents()
        counts = self.reads.incident_counts()
        # Refuse unsupported recovery claims rather than turn incomplete rows green.
        for row in self.reads.incident_rows(schemas.IncidentFilters(status="resolved")):
            self.require_recovery_evidence(row.id)
        return schemas.Summary(
            **counts,
            active_agents=sum(agent.status == "running" for agent in agents),
            current_runs=self.reads.active_run_count(),
            agent_statuses=agents,
            last_updated=utc_now(),
        )

    def safe_settings(self) -> schemas.SafeSettings:
        rows = self.reads.find(models.BackendSettings)
        if rows:
            return project(schemas.SafeSettings, rows[0])
        # Explicit safe configuration defaults, not operational observations or a seeded row.
        return schemas.SafeSettings(monitoring_interval_seconds=5, max_candidate_revisions=2)

    def overview(self) -> schemas.DashboardOverview:
        """Combine persisted metrics, activity and outcomes for supplementary consumers."""
        severities = self.reads.severity_counts()
        audit_rows = sorted(
            (row for row in self.reads.find(models.AuditEvent) if row.incident_id),
            key=lambda row: (row.occurred_at, row.id),
            reverse=True,
        )[:10]
        return schemas.DashboardOverview(
            summary=self.summary(),
            registered_applications=self.reads.application_count(),
            incidents_by_severity={kind: severities.get(kind, 0) for kind in Severity},
            recent_activity=[
                project(
                    schemas.Event,
                    row,
                    run_id=row.run_id or "",
                    actor_id=row.actor_key,
                    payload=row.payload_metadata,
                )
                for row in audit_rows
            ],
            recent_outcomes=list(reversed(self.reports()))[:10],
        )
