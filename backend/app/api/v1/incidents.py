"""Incidents endpoints ? full CRUD, filtering, pagination, workflow triggers."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import NotFoundError
from ...core.security import get_current_actor
from ...db.models import (
    ApplicationAttempt,
    ApprovalDecision,
    Diagnosis,
    Incident,
    IncidentEvent,
    IncidentReport,
    IncidentRun,
    PatchCandidate,
    ValidationResult,
    VerificationResult,
)
from ...db.session import get_db
from ...schemas.common import (
    ApiResponse,
    AttemptOut,
    CheckOut,
    DecisionOut,
    DiagnosisOut,
    EventOut,
    EvidenceOut,
    IncidentCreate,
    IncidentDetailOut,
    IncidentOut,
    Meta,
    Paginated,
    PatchOut,
    ReportOut,
    ValidationOut,
    VerificationOut,
)
from ...services.manager import ManagerAgent

router = APIRouter(tags=["incidents"])

CLOSED_STATES = {"resolved", "rejected", "unresolved", "reported"}
OPEN_STATES = {"detected", "diagnosing", "generating_patch", "validating",
               "revision_requested", "awaiting_approval", "approved",
               "applying", "verifying", "restoring", "manual_review", "error"}
ACTIVE_STATES = {"applying", "verifying", "validating", "diagnosing", "generating_patch"}


def _to_incident_out(inc: Incident) -> IncidentOut:
    return IncidentOut(
        id=inc.id,
        application_id=inc.application_id,
        source_event_id=inc.source_event_id,
        fingerprint=inc.fingerprint,
        severity=inc.severity,
        error_type=inc.error_type,
        message=inc.message,
        status=inc.status,
        current_stage=inc.current_stage,
        repository_revision=inc.repository_revision,
        active_run_id=inc.active_run_id,
        detected_at=inc.detected_at,
        resolved_at=inc.resolved_at,
    )


async def _build_incident_detail(
    inc: Incident, db: AsyncSession, actor_id: str
) -> IncidentDetailOut:
    """Build a full IncidentDetail with all nested objects."""
    # Latest diagnosis
    latest_diag = await db.scalar(
        select(Diagnosis).where(Diagnosis.incident_id == inc.id)
        .order_by(Diagnosis.created_at.desc())
    )
    diagnosis_out = None
    if latest_diag:
        evidence = json.loads(latest_diag.evidence_json)
        diagnosis_out = DiagnosisOut(
            incident_id=inc.id,
            run_id=latest_diag.run_id,
            status=latest_diag.status,
            hypothesis=latest_diag.hypothesis,
            confidence_label=latest_diag.confidence_label,
            uncertainty=latest_diag.uncertainty,
            suggested_direction=latest_diag.suggested_direction,
            evidence=[EvidenceOut(**e) for e in evidence],
        )

    # All patches
    candidates = (await db.scalars(
        select(PatchCandidate).where(PatchCandidate.incident_id == inc.id)
        .order_by(PatchCandidate.version)
    )).all()
    patches_out = []
    for c in candidates:
        patches_out.append(PatchOut(
            id=c.id,
            incident_id=inc.id,
            run_id=c.run_id,
            version=c.version,
            base_revision=c.base_revision,
            patch_hash=c.patch_hash,
            changed_files=json.loads(c.changed_files_json),
            rationale=c.rationale,
            diff_artifact_id=c.diff_artifact_id or "",
            status=c.status,
            diff=c.diff_content,
        ))

    # Latest validation
    validation_out = None
    if candidates:
        latest_candidate = candidates[-1]
        latest_val = await db.scalar(
            select(ValidationResult).where(ValidationResult.candidate_id == latest_candidate.id)
            .order_by(ValidationResult.created_at.desc())
        )
        if latest_val:
            checks = json.loads(latest_val.checks_json)
            validation_out = ValidationOut(
                candidate_id=latest_val.candidate_id,
                patch_hash=latest_val.patch_hash,
                status=latest_val.status,
                checks=[CheckOut(**c) for c in checks],
                environment_id=latest_val.environment_id,
                duration_ms=latest_val.duration_ms,
            )

    # Latest approval decision
    decision_out = None
    latest_decision = await db.scalar(
        select(ApprovalDecision).where(ApprovalDecision.incident_id == inc.id)
        .order_by(ApprovalDecision.decided_at.desc())
    )
    if latest_decision:
        decision_out = DecisionOut(
            id=latest_decision.id,
            incident_id=inc.id,
            candidate_id=latest_decision.candidate_id,
            patch_hash=latest_decision.patch_hash,
            base_revision=latest_decision.base_revision,
            decision=latest_decision.decision,
            actor_id=latest_decision.actor_id,
            comment=latest_decision.comment,
            decided_at=latest_decision.decided_at,
        )

    # Latest application attempt
    attempt_out = None
    if candidates:
        latest_candidate = candidates[-1]
        latest_attempt = await db.scalar(
            select(ApplicationAttempt).where(ApplicationAttempt.candidate_id == latest_candidate.id)
            .order_by(ApplicationAttempt.applied_at.desc())
        )
        if latest_attempt:
            attempt_out = AttemptOut(
                id=latest_attempt.id,
                candidate_id=latest_attempt.candidate_id,
                snapshot_ref=latest_attempt.snapshot_ref,
                before_revision=latest_attempt.before_revision,
                after_revision=latest_attempt.after_revision,
                status=latest_attempt.status,
                applied_at=latest_attempt.applied_at,
                restore_status=latest_attempt.restore_status,
            )

    # Verification
    verification_out = None
    if attempt_out:
        latest_attempt = await db.scalar(
            select(ApplicationAttempt).where(ApplicationAttempt.id == attempt_out.id)
        )
        if latest_attempt:
            latest_ver = await db.scalar(
                select(VerificationResult)
                .where(VerificationResult.application_attempt_id == latest_attempt.id)
                .order_by(VerificationResult.created_at.desc())
            )
            if latest_ver:
                checks = json.loads(latest_ver.checks_json)
                mon_obs = json.loads(latest_ver.monitoring_observation_json)
                verification_out = VerificationOut(
                    id=latest_ver.id,
                    application_attempt_id=latest_ver.application_attempt_id,
                    candidate_id=latest_ver.candidate_id,
                    status=latest_ver.status,
                    checks=[CheckOut(**c) for c in checks],
                    monitoring_observation=mon_obs.get("observation", ""),
                    evidence_artifact_id=latest_ver.evidence_artifact_id or "",
                )

    # Report
    report_out = None
    latest_report = await db.scalar(
        select(IncidentReport).where(IncidentReport.incident_id == inc.id)
        .order_by(IncidentReport.version.desc())
    )
    if latest_report:
        summary_data = json.loads(latest_report.summary_json)
        report_out = ReportOut(
            id=latest_report.id,
            incident_id=inc.id,
            version=latest_report.version,
            outcome=latest_report.outcome,
            report_artifact_id=latest_report.report_artifact_id,
            summary=summary_data.get("summary", ""),
            limitations=summary_data.get("limitations", []),
            generated_at=latest_report.generated_at,
        )

    # Permission flags ? derived from status and actor
    can_approve = inc.status == "awaiting_approval" and bool(candidates) and (
        candidates[-1].status == "validated" if candidates else False
    )
    can_reject = inc.status == "awaiting_approval"
    can_apply = (
        inc.status == "approved"
        and latest_decision is not None
        and latest_decision.decision == "approve"
        and bool(candidates)
        and (candidates[-1].status == "approved" if candidates else False)
    )

    perm_reason = _permission_reason(inc, can_approve, can_reject, can_apply, validation_out)

    return IncidentDetailOut(
        id=inc.id,
        application_id=inc.application_id,
        source_event_id=inc.source_event_id,
        fingerprint=inc.fingerprint,
        severity=inc.severity,
        error_type=inc.error_type,
        message=inc.message,
        status=inc.status,
        current_stage=inc.current_stage,
        repository_revision=inc.repository_revision,
        active_run_id=inc.active_run_id,
        detected_at=inc.detected_at,
        resolved_at=inc.resolved_at,
        source_log=inc.source_log,
        diagnosis=diagnosis_out,
        patches=patches_out,
        validation=validation_out,
        decision=decision_out,
        application_attempt=attempt_out,
        verification=verification_out,
        report=report_out,
        can_approve=can_approve,
        can_reject=can_reject,
        can_apply=can_apply,
        permission_reason=perm_reason,
    )


def _permission_reason(
    inc: Incident,
    can_approve: bool,
    can_reject: bool,
    can_apply: bool,
    validation: ValidationOut | None,
) -> str:
    if inc.status == "manual_review":
        return "Needs manual review. No supported diagnosis or candidate."
    if inc.status in CLOSED_STATES:
        return "This incident has been closed."
    if inc.status == "awaiting_approval":
        if not can_approve:
            if validation and validation.status != "passed":
                return "Failed validation. A candidate revision is required."
            return "Approval conditions not met."
    if inc.status == "approved" and not can_apply:
        return "Apply conditions not met."
    return ""


@router.get("/incidents", response_model=ApiResponse[Paginated[IncidentOut]])
async def list_incidents(
    request: Request,
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    severity: str | None = None,
    application_id: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
    search: str | None = None,
    scope: str | None = None,
    sort: str | None = None,
):
    request_id = getattr(request.state, "request_id", "")
    q = select(Incident)

    # Scope filter
    if scope == "open":
        q = q.where(~Incident.status.in_(list(CLOSED_STATES)))
    elif scope == "closed":
        q = q.where(Incident.status.in_(list(CLOSED_STATES)))
    elif scope == "candidates":
        from ...db.models import PatchCandidate as PC
        incident_ids_with_patches = select(PC.incident_id).distinct()
        q = q.where(Incident.id.in_(incident_ids_with_patches))
    elif scope == "pending":
        q = q.where(Incident.status.in_(["awaiting_approval", "approved"]))

    # Filters
    if status:
        q = q.where(Incident.status == status)
    if severity:
        q = q.where(Incident.severity == severity)
    if application_id:
        q = q.where(Incident.application_id == application_id)
    if search:
        q = q.where(or_(
            Incident.id.ilike(f"%{search}%"),
            Incident.error_type.ilike(f"%{search}%"),
            Incident.message.ilike(f"%{search}%"),
        ))

    # Sorting
    if sort == "detected_asc":
        q = q.order_by(Incident.detected_at.asc())
    elif sort == "severity_desc":
        q = q.order_by(Incident.detected_at.desc())  # simplified ? proper sort needs case()
    else:
        q = q.order_by(Incident.detected_at.desc())

    # Total count
    count_q = select(func.count()).select_from(q.subquery())
    total = await db.scalar(count_q) or 0

    # Cursor pagination (integer offset)
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    q = q.offset(offset).limit(limit)
    items = (await db.scalars(q)).all()

    next_cursor = str(offset + limit) if offset + limit < total else None
    return ApiResponse(
        data=Paginated(
            items=[_to_incident_out(i) for i in items],
            next_cursor=next_cursor,
            total=total,
        ),
        meta=Meta(request_id=request_id),
    )


@router.post("/incidents", response_model=ApiResponse[IncidentOut])
async def create_incident(
    body: IncidentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", "")
    get_current_actor(request)
    manager = ManagerAgent(db)
    incident, created = await manager.create_or_deduplicate_incident(
        application_id=body.application_id,
        source_event_id=body.source_event_id,
        fingerprint=body.fingerprint,
        severity=body.severity,
        error_type=body.error_type,
        message=body.message,
        source_log=body.source_log,
        repository_revision=body.repository_revision,
    )
    return ApiResponse(data=_to_incident_out(incident), meta=Meta(request_id=request_id))


@router.get("/incidents/{incident_id}", response_model=ApiResponse[IncidentDetailOut])
async def get_incident(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    actor = get_current_actor(request)
    inc = await db.scalar(select(Incident).where(Incident.id == incident_id))
    if not inc:
        raise NotFoundError("Incident")
    detail = await _build_incident_detail(inc, db, actor)
    return ApiResponse(data=detail, meta=Meta(request_id=request_id))


@router.get("/incidents/{incident_id}/events", response_model=ApiResponse[list[EventOut]])
async def get_incident_events(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    inc = await db.scalar(select(Incident).where(Incident.id == incident_id))
    if not inc:
        raise NotFoundError("Incident")
    events = (await db.scalars(
        select(IncidentEvent)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.occurred_at)
    )).all()
    return ApiResponse(
        data=[EventOut(
            id=e.id,
            incident_id=e.incident_id,
            run_id=e.run_id,
            event_type=e.event_type,
            actor_type=e.actor_type,
            actor_id=e.actor_id,
            payload=json.loads(e.payload_json),
            occurred_at=e.occurred_at,
        ) for e in events],
        meta=Meta(request_id=request_id),
    )


@router.post("/incidents/{incident_id}/runs", response_model=ApiResponse[dict])
async def start_run(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    actor = get_current_actor(request)
    idempotency_key = request.headers.get("Idempotency-Key")
    manager = ManagerAgent(db)
    run = await manager.start_run(incident_id, actor, idempotency_key)
    return ApiResponse(
        data={"run_id": run.id, "state": run.state, "attempt": run.attempt},
        meta=Meta(request_id=request_id),
    )


@router.get("/incidents/{incident_id}/runs", response_model=ApiResponse[list[dict]])
async def list_runs(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    runs = (await db.scalars(
        select(IncidentRun).where(IncidentRun.incident_id == incident_id)
        .order_by(IncidentRun.started_at)
    )).all()
    return ApiResponse(
        data=[{"id": r.id, "state": r.state, "attempt": r.attempt,
               "started_at": r.started_at.isoformat(), "finished_at": r.finished_at.isoformat() if r.finished_at else None}
              for r in runs],
        meta=Meta(request_id=request_id),
    )


@router.post("/incidents/{incident_id}/workflow/diagnose", response_model=ApiResponse[dict])
async def trigger_diagnosis(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Trigger the diagnosis stage for an incident."""
    request_id = getattr(request.state, "request_id", "")
    manager = ManagerAgent(db)
    result = await manager.run_diagnosis_stage(incident_id)
    return ApiResponse(data=result, meta=Meta(request_id=request_id))


@router.post("/incidents/{incident_id}/workflow/repair", response_model=ApiResponse[dict])
async def trigger_repair(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Trigger the repair stage for an incident."""
    request_id = getattr(request.state, "request_id", "")
    manager = ManagerAgent(db)
    result = await manager.run_repair_stage(incident_id)
    return ApiResponse(data=result, meta=Meta(request_id=request_id))


@router.post("/incidents/{incident_id}/workflow/test", response_model=ApiResponse[dict])
async def trigger_testing(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Trigger the testing stage for an incident."""
    request_id = getattr(request.state, "request_id", "")
    manager = ManagerAgent(db)
    result = await manager.run_testing_stage(incident_id)
    return ApiResponse(data=result, meta=Meta(request_id=request_id))


@router.post("/incidents/{incident_id}/workflow/run-all", response_model=ApiResponse[dict])
async def run_full_workflow(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Run the full automated workflow (diagnose ? repair ? test) for an incident."""
    request_id = getattr(request.state, "request_id", "")
    actor = get_current_actor(request)
    manager = ManagerAgent(db)

    # Start run first
    await manager.start_run(incident_id, actor)

    # Run automated stages
    diag_result = await manager.run_diagnosis_stage(incident_id)
    if diag_result.get("status") in {"manual_review", "error"}:
        return ApiResponse(data={"stage": "diagnosing", "status": "manual_review"}, meta=Meta(request_id=request_id))

    repair_result = await manager.run_repair_stage(incident_id)
    if repair_result.get("status") in {"unresolved", "manual_review", "error"}:
        return ApiResponse(data=repair_result, meta=Meta(request_id=request_id))

    test_result = await manager.run_testing_stage(incident_id)
    return ApiResponse(data=test_result, meta=Meta(request_id=request_id))


@router.get("/incidents/{incident_id}/diagnosis", response_model=ApiResponse[dict])
async def get_diagnosis(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    from ...db.models import Diagnosis
    diag = await db.scalar(
        select(Diagnosis).where(Diagnosis.incident_id == incident_id)
        .order_by(Diagnosis.created_at.desc())
    )
    if not diag:
        raise NotFoundError("Diagnosis")
    return ApiResponse(data={
        "incident_id": incident_id,
        "run_id": diag.run_id,
        "status": diag.status,
        "hypothesis": diag.hypothesis,
        "confidence_label": diag.confidence_label,
        "uncertainty": diag.uncertainty,
        "suggested_direction": diag.suggested_direction,
        "evidence": json.loads(diag.evidence_json),
    }, meta=Meta(request_id=request_id))


@router.get("/incidents/{incident_id}/patches", response_model=ApiResponse[list[PatchOut]])
async def list_patches_for_incident(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    inc = await db.scalar(select(Incident).where(Incident.id == incident_id))
    if not inc:
        raise NotFoundError("Incident")
    candidates = (await db.scalars(
        select(PatchCandidate).where(PatchCandidate.incident_id == incident_id)
        .order_by(PatchCandidate.version)
    )).all()
    return ApiResponse(
        data=[PatchOut(
            id=c.id, incident_id=incident_id, run_id=c.run_id, version=c.version,
            base_revision=c.base_revision, patch_hash=c.patch_hash,
            changed_files=json.loads(c.changed_files_json), rationale=c.rationale,
            diff_artifact_id=c.diff_artifact_id or "", status=c.status, diff=c.diff_content,
        ) for c in candidates],
        meta=Meta(request_id=request_id),
    )


@router.get("/incidents/{incident_id}/report", response_model=ApiResponse[ReportOut])
async def get_incident_report(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    inc = await db.scalar(select(Incident).where(Incident.id == incident_id))
    if not inc:
        raise NotFoundError("Incident")
    report = await db.scalar(
        select(IncidentReport).where(IncidentReport.incident_id == incident_id)
        .order_by(IncidentReport.version.desc())
    )
    if not report:
        raise NotFoundError("IncidentReport")
    summary_data = json.loads(report.summary_json)
    return ApiResponse(
        data=ReportOut(
            id=report.id,
            incident_id=incident_id,
            version=report.version,
            outcome=report.outcome,
            report_artifact_id=report.report_artifact_id,
            summary=summary_data.get("summary", ""),
            limitations=summary_data.get("limitations", []),
            generated_at=report.generated_at,
        ),
        meta=Meta(request_id=request_id),
    )


@router.get("/incidents/{incident_id}/reports", response_model=ApiResponse[list[ReportOut]])
async def list_incident_reports(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    reports = (await db.scalars(
        select(IncidentReport).where(IncidentReport.incident_id == incident_id)
        .order_by(IncidentReport.version)
    )).all()
    result = []
    for r in reports:
        summary_data = json.loads(r.summary_json)
        result.append(ReportOut(
            id=r.id, incident_id=incident_id, version=r.version, outcome=r.outcome,
            report_artifact_id=r.report_artifact_id,
            summary=summary_data.get("summary", ""),
            limitations=summary_data.get("limitations", []),
            generated_at=r.generated_at,
        ))
    return ApiResponse(data=result, meta=Meta(request_id=request_id))


@router.get("/incidents/{incident_id}/verification", response_model=ApiResponse[VerificationOut])
async def get_verification(
    incident_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", "")
    inc = await db.scalar(select(Incident).where(Incident.id == incident_id))
    if not inc:
        raise NotFoundError("Incident")
    # Get latest application attempt for this incident's candidates
    latest_candidate = await db.scalar(
        select(PatchCandidate).where(PatchCandidate.incident_id == incident_id)
        .order_by(PatchCandidate.version.desc())
    )
    if not latest_candidate:
        raise NotFoundError("ApplicationAttempt")
    latest_attempt = await db.scalar(
        select(ApplicationAttempt).where(ApplicationAttempt.candidate_id == latest_candidate.id)
        .order_by(ApplicationAttempt.applied_at.desc())
    )
    if not latest_attempt:
        raise NotFoundError("ApplicationAttempt")
    ver = await db.scalar(
        select(VerificationResult)
        .where(VerificationResult.application_attempt_id == latest_attempt.id)
        .order_by(VerificationResult.created_at.desc())
    )
    if not ver:
        raise NotFoundError("VerificationResult")
    checks = json.loads(ver.checks_json)
    mon_obs = json.loads(ver.monitoring_observation_json)
    return ApiResponse(
        data=VerificationOut(
            id=ver.id,
            application_attempt_id=ver.application_attempt_id,
            candidate_id=ver.candidate_id,
            status=ver.status,
            checks=[CheckOut(**c) for c in checks],
            monitoring_observation=mon_obs.get("observation", ""),
            evidence_artifact_id=ver.evidence_artifact_id or "",
        ),
        meta=Meta(request_id=request_id),
    )
