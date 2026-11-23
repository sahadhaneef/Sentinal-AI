"""Manager Agent ? persistent state machine coordinating the full workflow.

This is Delvin's core responsibility. It implements the full 15-state workflow
as a persistent, re-entrant state machine backed by the SQLite database.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..agents.registry import AgentInput, AgentOutput, AgentType, get_registry
from ..core.errors import ConflictError, NotFoundError
from ..core.logging import get_logger
from ..db.models import (
    AgentExecution,
    ApplicationAttempt,
    Artifact,
    Diagnosis,
    Incident,
    IncidentEvent,
    IncidentReport,
    IncidentRun,
    PatchCandidate,
    ValidationResult,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Canonical run states
TERMINAL_STATES = {
    "resolved", "rejected", "manual_review", "unresolved", "error", "reported"
}

ACTIVE_STATES = {
    "detected", "diagnosing", "generating_patch", "validating",
    "revision_requested", "awaiting_approval", "approved",
    "applying", "verifying", "restoring",
}

VALID_TRANSITIONS: dict[str, set[str]] = {
    "detected": {"diagnosing", "manual_review", "error"},
    "diagnosing": {"generating_patch", "manual_review", "error"},
    "generating_patch": {"validating", "manual_review", "error"},
    "validating": {"awaiting_approval", "revision_requested", "manual_review", "error"},
    "revision_requested": {"generating_patch", "unresolved", "error"},
    "awaiting_approval": {"approved", "rejected", "manual_review", "error"},
    "approved": {"applying", "error"},
    "applying": {"verifying", "restoring", "unresolved", "error"},
    "verifying": {"resolved", "restoring", "error"},
    "restoring": {"unresolved", "error"},
    "resolved": {"reported"},
    "rejected": {"reported"},
    "unresolved": {"reported"},
    "manual_review": {"reported"},
    "error": {"reported"},
    "reported": set(),
}


class ManagerAgent:
    """Persistent state machine that coordinates the SENTINEL AI workflow."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.registry = get_registry()

    # ?? Incident Management ???????????????????????????????????????????????????

    async def create_or_deduplicate_incident(
        self,
        application_id: str,
        source_event_id: str,
        fingerprint: str,
        severity: str,
        error_type: str,
        message: str,
        source_log: str,
        repository_revision: str,
    ) -> tuple[Incident, bool]:
        """Create a new incident or return existing one with same fingerprint."""
        from sqlalchemy import select

        existing = await self.session.scalar(
            select(Incident).where(Incident.fingerprint == fingerprint)
        )
        if existing:
            logger.info("Duplicate incident detected", extra={"fingerprint": fingerprint, "id": existing.id})
            return existing, False

        incident = Incident(
            id=f"inc_{str(uuid.uuid4())[:8]}",
            application_id=application_id,
            source_event_id=source_event_id,
            fingerprint=fingerprint,
            severity=severity,
            error_type=error_type,
            message=message,
            source_log=source_log,
            repository_revision=repository_revision,
            status="detected",
            current_stage="detected",
        )
        self.session.add(incident)
        await self.session.flush()

        await self._emit_event(
            incident_id=incident.id,
            run_id=None,
            event_type="detected",
            actor_type="agent",
            actor_id="monitoring",
            payload={"message": "Incident detected and deduplicated.", "fingerprint": fingerprint},
        )
        await self.session.commit()
        logger.info("Incident created", extra={"id": incident.id})
        return incident, True

    async def start_run(self, incident_id: str, actor_id: str, idempotency_key: str | None = None) -> IncidentRun:
        """Start a new workflow run. Prevents duplicate active runs."""
        from sqlalchemy import select

        incident = await self._get_incident(incident_id)

        # Check for active run
        if incident.active_run_id:
            existing_run = await self.session.scalar(
                select(IncidentRun).where(IncidentRun.id == incident.active_run_id)
            )
            if existing_run and existing_run.state not in TERMINAL_STATES:
                raise ConflictError(f"An active run {incident.active_run_id} already exists for this incident.")

        # Determine attempt number
        all_runs = (await self.session.scalars(
            select(IncidentRun).where(IncidentRun.incident_id == incident_id)
        )).all()
        attempt = len(all_runs) + 1

        run = IncidentRun(
            incident_id=incident_id,
            state="detected",
            attempt=attempt,
        )
        self.session.add(run)
        await self.session.flush()

        incident.active_run_id = run.id
        incident.status = "detected"
        incident.current_stage = "detected"

        await self._emit_event(
            incident_id=incident_id,
            run_id=run.id,
            event_type="run_started",
            actor_type="human",
            actor_id=actor_id,
            payload={"attempt": attempt},
        )
        await self.session.commit()
        return run

    # ?? State Machine ?????????????????????????????????????????????????????????

    async def _transition(
        self,
        incident: Incident,
        run: IncidentRun,
        new_state: str,
        actor_id: str = "manager",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Atomically transition to a new state with validation."""
        current = run.state
        if new_state not in VALID_TRANSITIONS.get(current, set()):
            raise ConflictError(f"Invalid transition: {current} ? {new_state}")

        run.state = new_state
        incident.status = new_state
        incident.current_stage = new_state

        if new_state in {"resolved", "reported"}:
            incident.resolved_at = datetime.now(UTC)
        if new_state in TERMINAL_STATES:
            run.finished_at = datetime.now(UTC)

        await self._emit_event(
            incident_id=incident.id,
            run_id=run.id,
            event_type=new_state,
            actor_type="system" if actor_id == "manager" else "human",
            actor_id=actor_id,
            payload=payload or {},
        )
        await self.session.flush()

    async def _emit_event(
        self,
        incident_id: str,
        run_id: str | None,
        event_type: str,
        actor_type: str,
        actor_id: str,
        payload: dict[str, Any],
    ) -> None:
        event = IncidentEvent(
            incident_id=incident_id,
            run_id=run_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload_json=json.dumps(payload),
        )
        self.session.add(event)

    async def _record_execution(
        self,
        run: IncidentRun,
        agent_type: str,
        status: str,
        input_revision: str,
        error_json: str | None = None,
        output_artifact_id: str | None = None,
        duration_ms: int = 0,
    ) -> AgentExecution:
        execution = AgentExecution(
            run_id=run.id,
            agent_type=agent_type,
            status=status,
            input_revision=input_revision,
            completed_at=datetime.now(UTC),
            duration_ms=duration_ms,
            error_json=error_json,
            output_artifact_id=output_artifact_id,
        )
        self.session.add(execution)
        await self.session.flush()
        return execution

    # ?? Workflow Stages ???????????????????????????????????????????????????????

    async def run_diagnosis_stage(self, incident_id: str) -> dict[str, Any]:
        """Stage 1: Run the Diagnosis Agent with timeout and schema normalization."""
        import asyncio

        incident, run = await self._get_incident_and_run(incident_id)
        if run.state != "diagnosing":
            await self._transition(incident, run, "diagnosing")

        start = datetime.now(UTC)
        inp = AgentInput(
            incident_id=incident_id,
            run_id=run.id,
            repository_revision=incident.repository_revision,
            extra={
                "source_log": incident.source_log,
                "error_type": incident.error_type,
                "error_message": incident.message,
                "application_id": incident.application_id,
            },
        )

        agent = self.registry.get(AgentType.DIAGNOSIS)
        try:
            output: AgentOutput = await asyncio.wait_for(
                agent.execute(inp),
                timeout=float(agent.timeout_seconds),
            )
        except TimeoutError:
            output = AgentOutput(
                success=False,
                error=f"Diagnosis Agent timed out after {agent.timeout_seconds} seconds.",
            )
        except Exception as exc:
            output = AgentOutput(success=False, error=str(exc))

        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

        if not output.success:
            await self._record_execution(
                run, "diagnosis", "error", incident.repository_revision,
                error_json=json.dumps({"error": output.error}), duration_ms=duration_ms
            )
            await self._transition(
                incident, run, "manual_review",
                payload={"reason": f"Diagnosis agent error: {output.error}"}
            )
            await self.session.commit()
            return {"stage": "diagnosing", "status": "manual_review", "error": output.error}

        data = output.data
        diagnosis_status = data.get("status", "completed")
        if diagnosis_status not in ("completed", "manual_review"):
            diagnosis_status = "manual_review"

        # Schema normalization for Sahad's module (supports hypothesis or root_cause)
        hypothesis = data.get("hypothesis") or data.get("root_cause", "")
        suggested_dir = data.get("suggested_direction") or data.get("suggested_fix", "")
        evidence_list = data.get("evidence") or data.get("affected_files", [])

        normalized_evidence = []
        for e in evidence_list:
            normalized_evidence.append({
                "file_path": e.get("file_path", ""),
                "symbol": e.get("symbol", ""),
                "start_line": int(e.get("start_line", 1)),
                "end_line": int(e.get("end_line", 1)),
                "repository_revision": e.get("repository_revision", incident.repository_revision),
                "artifact_id": e.get("artifact_id", f"art_code_{incident_id}"),
                "excerpt": e.get("excerpt", f"Code evidence in {e.get('file_path', '')}"),
            })

        # Persist diagnosis
        diag = Diagnosis(
            incident_id=incident_id,
            run_id=run.id,
            hypothesis=hypothesis,
            confidence_label=data.get("confidence_label", "low"),
            uncertainty=data.get("uncertainty", ""),
            suggested_direction=suggested_dir,
            evidence_json=json.dumps(normalized_evidence),
            status=diagnosis_status,
        )
        self.session.add(diag)

        await self._record_execution(
            run, "diagnosis", "completed", incident.repository_revision, duration_ms=duration_ms
        )

        if diagnosis_status == "manual_review":
            await self._transition(
                incident, run, "manual_review",
                payload={"reason": "No supported evidence found or uncertainty too high."}
            )
        else:
            await self._transition(
                incident, run, "generating_patch",
                payload={"hypothesis": hypothesis}
            )

        await self.session.commit()
        return {"stage": "diagnosing", "status": diagnosis_status, "data": data}

    async def run_repair_stage(self, incident_id: str) -> dict[str, Any]:
        """Stage 2: Run the Repair Agent to generate a patch candidate."""
        from sqlalchemy import select

        incident, run = await self._get_incident_and_run(incident_id)
        if run.state != "generating_patch":
            await self._transition(incident, run, "generating_patch")

        # Check retry limit
        all_candidates = (await self.session.scalars(
            select(PatchCandidate).where(PatchCandidate.incident_id == incident_id)
        )).all()

        from ..core.config import get_settings
        settings = get_settings()
        if len(all_candidates) >= settings.max_candidate_revisions:
            await self._transition(incident, run, "unresolved",
                                   payload={"reason": f"Max {settings.max_candidate_revisions} candidate revisions reached."})
            await self.session.commit()
            return {"stage": "generating_patch", "status": "unresolved", "reason": "Max retries reached."}

        start = datetime.now(UTC)
        inp = AgentInput(
            incident_id=incident_id,
            run_id=run.id,
            repository_revision=incident.repository_revision,
        )
        output: AgentOutput = await self.registry.dispatch(AgentType.REPAIR, inp)
        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

        if not output.success:
            await self._record_execution(run, "repair", "error", incident.repository_revision,
                                         error_json=json.dumps({"error": output.error}), duration_ms=duration_ms)
            await self._transition(incident, run, "manual_review",
                                   payload={"reason": f"Repair agent error: {output.error}"})
            await self.session.commit()
            return {"stage": "generating_patch", "status": "manual_review", "error": output.error}

        data = output.data
        version = len(all_candidates) + 1

        # Create artifact for the diff
        diff_artifact = Artifact(
            kind="diff",
            storage_key=f"diff_{incident_id}_v{version}",
            sha256="",
            content_type="text/plain",
            content=data.get("diff", ""),
        )
        self.session.add(diff_artifact)
        await self.session.flush()

        candidate = PatchCandidate(
            incident_id=incident_id,
            run_id=run.id,
            version=version,
            base_revision=data.get("base_revision", incident.repository_revision),
            patch_hash=data.get("patch_hash", "sha256:unknown"),
            diff_artifact_id=diff_artifact.id,
            diff_content=data.get("diff", ""),
            changed_files_json=json.dumps(data.get("changed_files", [])),
            rationale=data.get("rationale", ""),
            status="proposed",
        )
        self.session.add(candidate)
        await self.session.flush()

        await self._record_execution(run, "repair", "completed", incident.repository_revision,
                                     output_artifact_id=diff_artifact.id, duration_ms=duration_ms)
        await self._transition(incident, run, "validating",
                               payload={"candidate_id": candidate.id, "version": version})
        await self.session.commit()
        return {"stage": "generating_patch", "status": "validating", "candidate_id": candidate.id}

    async def run_testing_stage(self, incident_id: str) -> dict[str, Any]:
        """Stage 3: Run the Testing Agent on the latest candidate."""
        from sqlalchemy import select

        incident, run = await self._get_incident_and_run(incident_id)

        # Get latest candidate
        candidates = (await self.session.scalars(
            select(PatchCandidate)
            .where(PatchCandidate.incident_id == incident_id)
            .order_by(PatchCandidate.version.desc())
        )).all()

        if not candidates:
            await self._transition(incident, run, "manual_review",
                                   payload={"reason": "No patch candidate available for testing."})
            await self.session.commit()
            return {"stage": "validating", "status": "manual_review", "error": "No candidate."}

        candidate = candidates[0]

        start = datetime.now(UTC)
        inp = AgentInput(
            incident_id=incident_id,
            run_id=run.id,
            repository_revision=incident.repository_revision,
            extra={"candidate_id": candidate.id, "patch_hash": candidate.patch_hash},
        )
        output: AgentOutput = await self.registry.dispatch(AgentType.TESTING, inp)
        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

        data = output.data
        test_status = data.get("status", "failed")
        checks = data.get("checks", [])
        all_passed = test_status == "passed" and all(c.get("status") == "passed" for c in checks)

        # Persist validation result
        validation = ValidationResult(
            candidate_id=candidate.id,
            patch_hash=candidate.patch_hash,
            status=test_status,
            checks_json=json.dumps(checks),
            environment_id=data.get("environment_id", f"sandbox_{candidate.id}"),
            duration_ms=data.get("duration_ms", duration_ms),
        )
        self.session.add(validation)

        if all_passed:
            candidate.status = "validated"
            await self._record_execution(run, "testing", "completed", incident.repository_revision,
                                         output_artifact_id=validation.id, duration_ms=duration_ms)
            await self._transition(incident, run, "awaiting_approval",
                                   payload={"candidate_id": candidate.id, "test_status": "passed"})
        else:
            candidate.status = "failed"
            await self._record_execution(run, "testing", "error", incident.repository_revision,
                                         error_json=json.dumps({"status": test_status}), duration_ms=duration_ms)
            # Check retry limit
            from ..core.config import get_settings
            settings = get_settings()
            existing_versions = (await self.session.scalars(
                select(PatchCandidate).where(PatchCandidate.incident_id == incident_id)
            )).all()
            if len(existing_versions) < settings.max_candidate_revisions:
                await self._transition(incident, run, "revision_requested",
                                       payload={"reason": f"Testing failed: {test_status}", "attempt": len(existing_versions)})
            else:
                await self._transition(incident, run, "unresolved",
                                       payload={"reason": "Max candidate revisions reached; testing still failing."})

        await self.session.commit()
        return {
            "stage": "validating",
            "status": test_status,
            "all_passed": all_passed,
            "candidate_id": candidate.id,
        }

    async def run_reporting_stage(self, incident_id: str, outcome: str, actor_id: str = "manager") -> dict[str, Any]:
        """Final stage: Generate a report from actual workflow outcomes."""
        from sqlalchemy import select

        incident, run = await self._get_incident_and_run(incident_id)

        start = datetime.now(UTC)
        inp = AgentInput(
            incident_id=incident_id,
            run_id=run.id,
            repository_revision=incident.repository_revision,
            extra={"outcome": outcome},
        )
        output: AgentOutput = await self.registry.dispatch(AgentType.REPORTING, inp)
        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

        data = output.data
        summary = data.get("summary", f"Incident {incident_id} outcome: {outcome}")
        limitations = data.get("limitations", ["STUB report ? limited evidence."])

        # Count existing reports
        existing_reports = (await self.session.scalars(
            select(IncidentReport).where(IncidentReport.incident_id == incident_id)
        )).all()
        version = len(existing_reports) + 1

        # Create report artifact
        report_artifact = Artifact(
            kind="report",
            storage_key=f"report_{incident_id}_v{version}",
            content_type="text/markdown",
            content=summary,
        )
        self.session.add(report_artifact)
        await self.session.flush()

        report = IncidentReport(
            incident_id=incident_id,
            version=version,
            outcome=outcome,
            report_artifact_id=report_artifact.id,
            summary_json=json.dumps({"summary": summary, "limitations": limitations}),
        )
        self.session.add(report)
        await self._record_execution(run, "reporting", "completed", incident.repository_revision, duration_ms=duration_ms)

        # Transition to reported
        try:
            await self._transition(incident, run, "reported",
                                   payload={"outcome": outcome, "version": version})
        except ConflictError:
            pass  # Already reported

        await self.session.commit()
        return {
            "stage": "reporting",
            "status": "reported",
            "outcome": outcome,
            "report_id": report.id,
        }

    # ?? Approval Gate ?????????????????????????????????????????????????????????

    async def approve_candidate(
        self,
        incident_id: str,
        candidate_id: str,
        patch_hash: str,
        base_revision: str,
        decision: str,
        actor_id: str,
        comment: str | None,
    ) -> dict[str, Any]:
        """Human approval gate ? enforces all security invariants."""
        from sqlalchemy import select

        from ..core.errors import (
            CandidateStaleError,
            TestsNotPassedError,
        )

        incident, run = await self._get_incident_and_run(incident_id)

        if incident.status != "awaiting_approval":
            raise ConflictError("This incident is not awaiting an approval decision.")

        # Retrieve and verify candidate
        candidate = await self.session.scalar(
            select(PatchCandidate).where(
                PatchCandidate.id == candidate_id,
                PatchCandidate.incident_id == incident_id,
            )
        )
        if not candidate:
            raise NotFoundError("PatchCandidate")

        # Security checks ? server enforces independently of frontend
        if candidate.patch_hash != patch_hash:
            raise CandidateStaleError()
        if candidate.base_revision != base_revision:
            raise CandidateStaleError()
        if candidate.status == "stale":
            raise CandidateStaleError()

        # Verify application revision hasn't changed
        from ..db.models import Application
        app = await self.session.scalar(select(Application).where(Application.id == incident.application_id))
        if app and app.repository_revision != base_revision:
            candidate.status = "stale"
            raise CandidateStaleError()

        if decision == "approve":
            # Verify tests passed ? never approve failed tests
            latest_validation = await self.session.scalar(
                select(ValidationResult)
                .where(ValidationResult.candidate_id == candidate_id)
                .order_by(ValidationResult.created_at.desc())
            )
            if not latest_validation or latest_validation.status != "passed":
                raise TestsNotPassedError()

            # Verify all individual checks passed
            checks = json.loads(latest_validation.checks_json)
            if not all(c.get("status") == "passed" for c in checks):
                raise TestsNotPassedError()

        from ..db.models import ApprovalDecision
        decision_record = ApprovalDecision(
            incident_id=incident_id,
            candidate_id=candidate_id,
            patch_hash=patch_hash,
            base_revision=base_revision,
            decision=decision,
            actor_id=actor_id,
            comment=comment,
        )
        self.session.add(decision_record)

        if decision == "approve":
            candidate.status = "approved"
            await self._transition(incident, run, "approved",
                                   actor_id=actor_id,
                                   payload={"candidate_id": candidate_id, "actor": actor_id})
        else:
            candidate.status = "rejected"
            await self._transition(incident, run, "rejected",
                                   actor_id=actor_id,
                                   payload={"reason": comment or "Reviewer rejected candidate."})
            # Generate rejection report immediately
            await self.session.commit()
            await self.run_reporting_stage(incident_id, "rejected", actor_id)
            await self.session.refresh(decision_record)
            return {
                "id": decision_record.id,
                "incident_id": incident_id,
                "candidate_id": candidate_id,
                "patch_hash": patch_hash,
                "base_revision": base_revision,
                "decision": decision,
                "actor_id": actor_id,
                "comment": comment,
                "decided_at": decision_record.decided_at.isoformat(),
            }

        await self.session.commit()
        await self.session.refresh(decision_record)
        return {
            "id": decision_record.id,
            "incident_id": incident_id,
            "candidate_id": candidate_id,
            "patch_hash": patch_hash,
            "base_revision": base_revision,
            "decision": decision,
            "actor_id": actor_id,
            "comment": comment,
            "decided_at": decision_record.decided_at.isoformat(),
        }

    async def apply_approved_patch(
        self,
        incident_id: str,
        candidate_id: str,
        patch_hash: str,
        base_revision: str,
    ) -> dict[str, Any]:
        """Controlled local application ? enforces all safety invariants."""
        from sqlalchemy import select

        from ..core.errors import ApprovalRequiredError, CandidateStaleError, TestsNotPassedError
        from ..services.apply import PatchApplicationService

        incident, run = await self._get_incident_and_run(incident_id)

        if incident.status != "approved":
            raise ApprovalRequiredError()

        candidate = await self.session.scalar(
            select(PatchCandidate).where(
                PatchCandidate.id == candidate_id,
                PatchCandidate.incident_id == incident_id,
            )
        )
        if not candidate:
            raise NotFoundError("PatchCandidate")

        # Security re-verification
        if candidate.patch_hash != patch_hash:
            raise CandidateStaleError()
        if candidate.base_revision != base_revision:
            raise CandidateStaleError()
        if candidate.status not in ("approved",):
            raise ApprovalRequiredError()

        # Verify approval decision exists
        from ..db.models import ApprovalDecision
        approval = await self.session.scalar(
            select(ApprovalDecision).where(
                ApprovalDecision.incident_id == incident_id,
                ApprovalDecision.candidate_id == candidate_id,
                ApprovalDecision.patch_hash == patch_hash,
                ApprovalDecision.base_revision == base_revision,
                ApprovalDecision.decision == "approve",
            )
        )
        if not approval:
            raise ApprovalRequiredError()

        # Re-verify tests passed
        latest_validation = await self.session.scalar(
            select(ValidationResult)
            .where(ValidationResult.candidate_id == candidate_id)
            .order_by(ValidationResult.created_at.desc())
        )
        if not latest_validation or latest_validation.status != "passed":
            raise TestsNotPassedError()

        await self._transition(incident, run, "applying",
                               payload={"candidate_id": candidate_id})

        # Delegate to PatchApplicationService
        apply_service = PatchApplicationService(self.session)
        attempt_data = await apply_service.apply(
            incident=incident,
            run=run,
            candidate=candidate,
        )

        attempt_id = attempt_data["attempt_id"]
        attempt = await self.session.scalar(
            select(ApplicationAttempt).where(ApplicationAttempt.id == attempt_id)
        )

        if attempt_data["status"] == "resolved":
            candidate.status = "applied"
            await self._transition(incident, run, "resolved",
                                   payload={"after_revision": attempt.after_revision})
            await self.session.commit()
            await self.run_reporting_stage(incident_id, "resolved")
        else:
            candidate.status = "failed"
            await self._transition(incident, run, "unresolved",
                                   payload={"reason": f"Verification failed; snapshot restored. {attempt_data.get('error', '')}"})
            await self.session.commit()
            await self.run_reporting_stage(incident_id, "unresolved")

        return attempt_data

    # ?? Interrupted Workflow Recovery ?????????????????????????????????????????

    async def resume_interrupted_workflows(self) -> list[dict[str, Any]]:
        """Scan DB for active non-terminal runs and resume or transition them safely."""
        from sqlalchemy import select

        active_incidents = (await self.session.scalars(
            select(Incident).where(Incident.status.in_(list(ACTIVE_STATES)))
        )).all()

        resumed: list[dict[str, Any]] = []
        for inc in active_incidents:
            if not inc.active_run_id:
                continue
            run = await self.session.scalar(
                select(IncidentRun).where(IncidentRun.id == inc.active_run_id)
            )
            if not run or run.state in TERMINAL_STATES:
                continue

            logger.info("Resuming interrupted workflow", extra={"incident_id": inc.id, "state": run.state})
            await self._emit_event(
                incident_id=inc.id,
                run_id=run.id,
                event_type="workflow_resumed",
                actor_type="system",
                actor_id="manager",
                payload={"resumed_from_state": run.state, "reason": "Server restarted or workflow recovered."},
            )

            # Depending on state, resume appropriately
            if run.state in ("detected", "diagnosing"):
                res = await self.run_diagnosis_stage(inc.id)
                resumed.append({"incident_id": inc.id, "action": "diagnosed", "result": res})
            elif run.state in ("generating_patch", "revision_requested"):
                res = await self.run_repair_stage(inc.id)
                resumed.append({"incident_id": inc.id, "action": "repaired", "result": res})
            elif run.state == "validating":
                res = await self.run_testing_stage(inc.id)
                resumed.append({"incident_id": inc.id, "action": "tested", "result": res})
            elif run.state == "awaiting_approval":
                # Preserved safely ? wait for human decision
                resumed.append({"incident_id": inc.id, "action": "preserved_awaiting_approval"})
            elif run.state in ("applying", "verifying"):
                # System crashed during apply/verify ? safely mark unresolved with audit event
                await self._transition(
                    inc, run, "unresolved",
                    payload={"reason": "Interrupted during patch application/verification; marked unresolved for safety."}
                )
                await self.session.commit()
                await self.run_reporting_stage(inc.id, "unresolved")
                resumed.append({"incident_id": inc.id, "action": "recovered_unresolved"})

        await self.session.commit()
        return resumed

    # ?? Helper Methods ????????????????????????????????????????????????????????

    async def _get_incident(self, incident_id: str) -> Incident:
        from sqlalchemy import select
        incident = await self.session.scalar(
            select(Incident).where(Incident.id == incident_id)
        )
        if not incident:
            raise NotFoundError("Incident")
        return incident

    async def _get_incident_and_run(self, incident_id: str) -> tuple[Incident, IncidentRun]:
        from sqlalchemy import select
        incident = await self._get_incident(incident_id)
        if not incident.active_run_id:
            raise ConflictError("No active run for this incident. Start a run first.")
        run = await self.session.scalar(
            select(IncidentRun).where(IncidentRun.id == incident.active_run_id)
        )
        if not run:
            raise NotFoundError("IncidentRun")
        return incident, run
