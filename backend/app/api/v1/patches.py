"""Patches and validation endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import NotFoundError
from ...db.models import PatchCandidate, ValidationResult
from ...db.session import get_db
from ...schemas.common import ApiResponse, CheckOut, Meta, PatchOut, ValidationOut

router = APIRouter(tags=["patches"])


@router.get("/patches/{candidate_id}", response_model=ApiResponse[PatchOut])
async def get_patch(candidate_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    candidate = await db.scalar(select(PatchCandidate).where(PatchCandidate.id == candidate_id))
    if not candidate:
        raise NotFoundError("PatchCandidate")
    return ApiResponse(
        data=PatchOut(
            id=candidate.id,
            incident_id=candidate.incident_id,
            run_id=candidate.run_id,
            version=candidate.version,
            base_revision=candidate.base_revision,
            patch_hash=candidate.patch_hash,
            changed_files=json.loads(candidate.changed_files_json),
            rationale=candidate.rationale,
            diff_artifact_id=candidate.diff_artifact_id or "",
            status=candidate.status,
            diff=candidate.diff_content,
        ),
        meta=Meta(request_id=request_id),
    )


@router.get("/patches/{candidate_id}/validation", response_model=ApiResponse[ValidationOut])
async def get_validation(candidate_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    request_id = getattr(request.state, "request_id", "")
    candidate = await db.scalar(select(PatchCandidate).where(PatchCandidate.id == candidate_id))
    if not candidate:
        raise NotFoundError("PatchCandidate")
    validation = await db.scalar(
        select(ValidationResult).where(ValidationResult.candidate_id == candidate_id)
        .order_by(ValidationResult.created_at.desc())
    )
    if not validation:
        raise NotFoundError("ValidationResult")
    checks = json.loads(validation.checks_json)
    return ApiResponse(
        data=ValidationOut(
            candidate_id=validation.candidate_id,
            patch_hash=validation.patch_hash,
            status=validation.status,
            checks=[CheckOut(**c) for c in checks],
            environment_id=validation.environment_id,
            duration_ms=validation.duration_ms,
        ),
        meta=Meta(request_id=request_id),
    )
