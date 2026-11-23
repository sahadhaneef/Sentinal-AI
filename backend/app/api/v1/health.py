"""Health endpoint."""
from fastapi import APIRouter, Request

from ...schemas.common import ApiResponse, HealthOut, Meta

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthOut])
async def health(request: Request):
    request_id = getattr(request.state, "request_id", "")
    return ApiResponse(
        data=HealthOut(status="ok", version="1.0.0"),
        meta=Meta(request_id=request_id),
    )
