from fastapi import APIRouter, Request

from app import __version__
from app.schemas.common import Envelope, Meta
from app.schemas.health import Health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Envelope[Health], summary="Backend process liveness")
def get_health(request: Request) -> Envelope[Health]:
    """The process started successfully; this does not claim agents or recovery are running."""
    return Envelope(
        data=Health(status="ok", version=__version__),
        meta=Meta(request_id=request.state.request_id),
    )
