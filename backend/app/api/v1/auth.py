"""Authentication and session management router."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...core.security import (
    _CSRF_COOKIE,
    _SESSION_COOKIE,
    create_csrf_token,
    create_session_token,
    get_current_actor,
)
from ...schemas.common import ApiResponse, Meta

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    role: Literal["reviewer", "admin", "operator"] = "reviewer"


class ActorOut(BaseModel):
    actor_id: str
    authenticated: bool
    role: str


@router.post("/login", response_model=ApiResponse[ActorOut])
async def login(body: LoginRequest, request: Request, response: Response):
    """Authenticate and issue signed session and CSRF cookies."""
    settings = get_settings()
    request_id = getattr(request.state, "request_id", "")

    actor_id = body.username.strip()
    session_token = create_session_token(actor_id)
    csrf_token = create_csrf_token()

    response.set_cookie(
        _SESSION_COOKIE,
        session_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        _CSRF_COOKIE,
        csrf_token,
        max_age=settings.session_max_age_seconds,
        httponly=False,
        samesite="lax",
    )

    return ApiResponse(
        data=ActorOut(actor_id=actor_id, authenticated=True, role=body.role),
        meta=Meta(request_id=request_id),
    )


@router.post("/logout", response_model=ApiResponse[dict])
async def logout(request: Request, response: Response):
    """Clear session and CSRF cookies."""
    request_id = getattr(request.state, "request_id", "")
    response.delete_cookie(_SESSION_COOKIE)
    response.delete_cookie(_CSRF_COOKIE)
    return ApiResponse(data={"message": "Logged out successfully."}, meta=Meta(request_id=request_id))


@router.get("/me", response_model=ApiResponse[ActorOut])
async def get_me(request: Request):
    """Get current reviewer identity."""
    request_id = getattr(request.state, "request_id", "")
    actor = get_current_actor(request)
    if not actor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return ApiResponse(
        data=ActorOut(actor_id=actor, authenticated=True, role="reviewer"),
        meta=Meta(request_id=request_id),
    )
