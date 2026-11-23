"""Synthetic persistence fixtures only; never served as live agent/test results."""

from datetime import timedelta

from app import models as M
from app.models.enums import AgentType, CheckStatus, RunState
from app.repositories import transaction
from app.repositories.incident import MonitoringInput
from tests.database.conftest import FINGERPRINT, HASH, HASH2, NOW


def event(**changes) -> MonitoringInput:
    values = dict(
        application_id="app_demo",
        repository_revision="demoabc",
        source_event_id="event_001",
        fingerprint=FINGERPRINT,
        severity="high",
        error_type="KeyError",
        message="Synthetic persistence fixture",
        occurred_at=NOW,
        log_artifact_id="art_log",
    )
    return MonitoringInput(**(values | changes))


def seed_minimal(engine) -> None:
    with transaction(engine) as store:
        for name, kind in [
            ("snapshot", "source_snapshot"),
            ("log", "log"),
            ("source", "source_excerpt"),
            ("diff", "diff"),
            ("test", "test_output"),
            ("verification", "verification"),
            ("report", "report"),
        ]:
            store.records(M.Artifact).add(
                M.Artifact(
                    id=f"art_{name}",
                    kind=kind,
                    storage_key=f"fixtures/{name}.txt",
                    sha256=HASH,
                    content_type="text/plain",
                    size_bytes=12,
                    redacted=True,
                )
            )
        store.users.add(M.User(id="reviewer", username="reviewer", display_name="Fixture reviewer"))
        role = store.records(M.Role).add(M.Role(id="role_reviewer", name="reviewer"))
        store.records(M.UserRole).add(M.UserRole(user_id="reviewer", role_id=role.id))
        store.applications.add(
            M.Application(id="app_demo", name="Fixture app", workspace_key="demo")
        )
        store.records(M.RepositoryRevision).add(
            M.RepositoryRevision(
                id="revision_001",
                application_id="app_demo",
                revision="demoabc",
                snapshot_artifact_id="art_snapshot",
            )
        )
        store.applications.select_revision("app_demo", "revision_001")


def seed_graph(engine) -> None:
    with transaction(engine) as store:
        _, incident = store.incidents.record_monitoring_event(event())
        store.records(M.WorkflowRun).add(
            M.WorkflowRun(
                id="run_001",
                incident_id=incident.id,
                application_id="app_demo",
                repository_revision="demoabc",
                state=RunState.AWAITING_APPROVAL,
                started_at=NOW,
            )
        )
        store.records(M.StageTransition).add(
            M.StageTransition(
                run_id="run_001",
                sequence=1,
                from_state=None,
                to_state=RunState.DETECTED,
                reason="Synthetic fixture record",
                occurred_at=NOW,
            )
        )
        for kind in AgentType:
            store.records(M.AgentExecution).add(
                M.AgentExecution(
                    run_id="run_001",
                    application_id="app_demo",
                    input_revision="demoabc",
                    agent_type=kind,
                    stage=kind.value,
                )
            )
        store.records(M.CodeIndexEntry).add(
            M.CodeIndexEntry(
                id="code_001",
                application_id="app_demo",
                repository_revision="demoabc",
                file_path="src/registration.py",
                symbol="register",
                start_line=1,
                end_line=10,
                content_hash=HASH,
                artifact_id="art_source",
            )
        )
        store.records(M.Diagnosis).add(
            M.Diagnosis(
                id="diagnosis_001",
                run_id="run_001",
                application_id="app_demo",
                repository_revision="demoabc",
                status="completed",
                hypothesis="Fixture only",
                confidence_label="low",
                uncertainty="Not an executed diagnosis",
                suggested_direction="Review",
            )
        )
        store.records(M.EvidenceReference).add(
            M.EvidenceReference(
                diagnosis_id="diagnosis_001",
                code_index_entry_id="code_001",
                application_id="app_demo",
                repository_revision="demoabc",
            )
        )
        store.patches.add(
            M.PatchCandidate(
                id="patch_001",
                incident_id=incident.id,
                run_id="run_001",
                application_id="app_demo",
                version=1,
                base_revision="demoabc",
                patch_hash=HASH,
                changed_files=["src/registration.py"],
                rationale="Synthetic record only",
                diff_artifact_id="art_diff",
            )
        )
        store.records(M.ValidationResult).add(
            M.ValidationResult(
                id="validation_001",
                candidate_id="patch_001",
                patch_hash=HASH,
                status=CheckStatus.PASSED,
                environment_id="fixture",
                evidence_artifact_id="art_test",
            )
        )
        store.records(M.ValidationCheck).add(
            M.ValidationCheck(
                validation_id="validation_001",
                name="fixture_check",
                status=CheckStatus.PASSED,
                exit_code=0,
                evidence_artifact_id="art_test",
            )
        )
        store.records(M.ApprovalDecision).add(
            M.ApprovalDecision(
                id="decision_001",
                candidate_id="patch_001",
                incident_id=incident.id,
                patch_hash=HASH,
                base_revision="demoabc",
                decision="approve",
                actor_id="reviewer",
                validation_id="validation_001",
                validation_status=CheckStatus.PASSED,
            )
        )
        store.records(M.ApplicationAttempt).add(
            M.ApplicationAttempt(
                id="attempt_001",
                application_id="app_demo",
                candidate_id="patch_001",
                approval_id="decision_001",
                patch_hash=HASH,
                before_revision="demoabc",
                snapshot_artifact_id="art_snapshot",
                status="unresolved",
                restore_status="restored",
            )
        )
        store.records(M.VerificationResult).add(
            M.VerificationResult(
                id="verification_001",
                application_attempt_id="attempt_001",
                candidate_id="patch_001",
                status=CheckStatus.FAILED,
                monitoring_observation="Fixture only; no code executed",
                evidence_artifact_id="art_verification",
            )
        )
        store.records(M.VerificationCheck).add(
            M.VerificationCheck(
                verification_id="verification_001",
                name="fixture_smoke",
                status=CheckStatus.FAILED,
                exit_code=1,
                evidence_artifact_id="art_verification",
            )
        )
        store.records(M.IncidentReport).add(
            M.IncidentReport(
                incident_id=incident.id,
                version=1,
                outcome=RunState.UNRESOLVED,
                report_artifact_id="art_report",
                summary="Synthetic persistence record",
                limitations=["No real agent or execution activity"],
            )
        )
        store.records(M.AuditEvent).add(
            M.AuditEvent(
                incident_id=incident.id,
                application_id="app_demo",
                run_id="run_001",
                event_type="fixture",
                actor_type="human",
                actor_user_id="reviewer",
                actor_key="reviewer",
            )
        )
        store.records(M.AuthSession).add(
            M.AuthSession(
                user_id="reviewer",
                token_hash=HASH2,
                expires_at=NOW + timedelta(days=500),
            )
        )
        store.records(M.IdempotencyRecord).add(
            M.IdempotencyRecord(
                actor_user_id="reviewer",
                operation="fixture",
                key="fixture-key",
                request_hash=HASH,
            )
        )
        store.records(M.BackendSettings).add(M.BackendSettings())
        store.incidents.update(incident.id, status=RunState.UNRESOLVED)
        store.records(M.WorkflowRun).update("run_001", state=RunState.UNRESOLVED, finished_at=NOW)
