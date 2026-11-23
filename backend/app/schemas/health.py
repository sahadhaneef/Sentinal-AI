from typing import Literal

from app.schemas.common import WireModel


class Health(WireModel):
    status: Literal["ok", "degraded"]
    version: str
