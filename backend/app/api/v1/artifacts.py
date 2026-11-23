"""Artifacts endpoints for sanitized logs, diffs, and evidence inspection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.errors import NotFoundError
from ...db.models import Artifact
from ...db.session import get_db
from ...schemas.common import ApiResponse, Meta

router = APIRouter(tags=["artifacts"])


class ArtifactOut(BaseModel):
    id: str
    kind: str
    storage_key: str
    sha256: str
    content_type: str
    redacted: bool
    size_bytes: int
    content: str


@router.get("/artifacts/{artifact_id}", response_model=ApiResponse[ArtifactOut])
async def get_artifact(
    artifact_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve sanitized artifact content by ID."""
    request_id = getattr(request.state, "request_id", "")
    artifact = await db.scalar(select(Artifact).where(Artifact.id == artifact_id))
    if not artifact:
        raise NotFoundError("Artifact")

    return ApiResponse(
        data=ArtifactOut(
            id=artifact.id,
            kind=artifact.kind,
            storage_key=artifact.storage_key,
            sha256=artifact.sha256,
            content_type=artifact.content_type,
            redacted=artifact.redacted,
            size_bytes=artifact.size_bytes or len(artifact.content),
            content=artifact.content,
        ),
        meta=Meta(request_id=request_id),
    )
