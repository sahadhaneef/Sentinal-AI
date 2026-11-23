"""Thin Phase 3 REST handlers over injected database-backed application services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app import models
from app.api.dependencies.domain import IntakeDependency, ReadDependency, require_operator
from app.core.errors import ApiError
from app.models.enums import AgentType
from app.repositories.errors import NotFound
from app.schemas import domain as schemas
from app.schemas.common import Envelope, ErrorEnvelope, Meta

router = APIRouter(responses={code: {"model": ErrorEnvelope} for code in (401, 403, 409, 503)})
UNAVAILABLE_RESPONSES = {
    501: {"model": ErrorEnvelope, "description": "Deliberately unavailable in this backend phase."}
}


def response[T](request: Request, data: T) -> Envelope[T]:
    """Attach the existing server-generated correlation envelope."""
    return Envelope(data=data, meta=Meta(request_id=request.state.request_id))


@router.get("/applications", response_model=Envelope[list[schemas.Application]])
def applications(request: Request, service: ReadDependency) -> Envelope:
    return response(request, service.applications())


@router.post(
    "/applications",
    response_model=Envelope[schemas.Application],
    status_code=201,
    dependencies=[Depends(require_operator)],
)
def register_application(
    request: Request,
    body: schemas.ApplicationRegistration,
    intake: IntakeDependency,
    service: ReadDependency,
) -> Envelope:
    return response(request, service.application(intake.register(body)))


@router.get("/applications/{identity}", response_model=Envelope[schemas.Application])
def application(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    return response(request, service.application(service.store.applications.get(identity)))


@router.get(
    "/applications/{identity}/metadata", response_model=Envelope[schemas.ApplicationMetadata]
)
def application_metadata(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    return response(request, service.application_metadata(identity))


@router.get("/incidents", response_model=Envelope[schemas.Page[schemas.Incident]])
def incidents(
    request: Request, service: ReadDependency, filters: Annotated[schemas.IncidentFilters, Query()]
) -> Envelope:
    if any(len(request.query_params.getlist(key)) != 1 for key in request.query_params):
        raise ApiError(422, "VALIDATION_ERROR", "Repeated query parameters are not supported.")
    return response(request, service.incidents(filters))


@router.post(
    "/incidents",
    response_model=Envelope[schemas.Incident],
    dependencies=[Depends(require_operator)],
)
def ingest_incident(
    request: Request,
    body: schemas.IncidentIngestion,
    intake: IntakeDependency,
    service: ReadDependency,
) -> Envelope:
    # 200 is stable for both first receipt and an exact idempotent replay.
    return response(request, service.incident(intake.ingest(body)))


@router.get("/incidents/{identity}", response_model=Envelope[schemas.IncidentDetail])
def incident(request: Request, identity: schemas.Identifier, service: ReadDependency) -> Envelope:
    return response(request, service.incident_detail(identity))


@router.get("/incidents/{identity}/events", response_model=Envelope[list[schemas.Event]])
def incident_events(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    return response(request, service.events(identity))


@router.get("/incidents/{identity}/runs", response_model=Envelope[list[schemas.RunDetail]])
def incident_runs(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    return response(request, service.runs(identity))


@router.get("/incidents/{identity}/diagnosis", response_model=Envelope[schemas.Diagnosis])
def diagnosis(request: Request, identity: schemas.Identifier, service: ReadDependency) -> Envelope:
    return response(request, service.diagnosis(identity))


@router.get("/incidents/{identity}/patches", response_model=Envelope[list[schemas.Patch]])
def patches(request: Request, identity: schemas.Identifier, service: ReadDependency) -> Envelope:
    return response(request, service.patches(identity))


@router.get("/patches/{identity}", response_model=Envelope[schemas.Patch])
def patch(request: Request, identity: schemas.Identifier, service: ReadDependency) -> Envelope:
    return response(request, service.patch(service.store.patches.get(identity)))


@router.get("/patches/{identity}/validation", response_model=Envelope[schemas.Validation])
def validation(request: Request, identity: schemas.Identifier, service: ReadDependency) -> Envelope:
    return response(request, service.validation(identity))


@router.get("/agents", response_model=Envelope[list[schemas.Agent]])
def agents(request: Request, service: ReadDependency) -> Envelope:
    return response(request, service.agents())


@router.get("/agents/{agent_type}", response_model=Envelope[schemas.AgentDetail])
def agent(request: Request, agent_type: AgentType, service: ReadDependency) -> Envelope:
    return response(request, service.agent(agent_type))


@router.get("/dashboard/summary", response_model=Envelope[schemas.Summary])
def dashboard(request: Request, service: ReadDependency) -> Envelope:
    return response(request, service.summary())


@router.get("/dashboard/overview", response_model=Envelope[schemas.DashboardOverview])
def overview(request: Request, service: ReadDependency) -> Envelope:
    return response(request, service.overview())


@router.get("/settings", response_model=Envelope[schemas.SafeSettings])
def settings(request: Request, service: ReadDependency) -> Envelope:
    return response(request, service.safe_settings())


@router.get("/reports", response_model=Envelope[list[schemas.Report]])
def reports(request: Request, service: ReadDependency) -> Envelope:
    return response(request, service.reports())


@router.get("/reports/{identity}", response_model=Envelope[schemas.Report])
def report_detail(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    return response(
        request, service.report(service.store.records(models.IncidentReport).get(identity))
    )


@router.get("/incidents/{identity}/reports", response_model=Envelope[list[schemas.Report]])
def incident_reports(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    return response(request, service.reports(identity))


@router.get("/incidents/{identity}/report", response_model=Envelope[schemas.Report])
def latest_report(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    rows = service.reports(identity)
    if not rows:
        raise NotFound("A report has not been recorded.")
    return response(request, rows[-1])


@router.get("/incidents/{identity}/verification", response_model=Envelope[schemas.Verification])
def latest_verification(
    request: Request, identity: schemas.Identifier, service: ReadDependency
) -> Envelope:
    return response(request, service.latest_verification(identity))


@router.get("/artifacts/{identity}", response_model=Envelope[schemas.ArtifactMetadata])
def artifact(request: Request, identity: schemas.Identifier, service: ReadDependency) -> Envelope:
    return response(request, service.artifacts.metadata(identity))


@router.post("/incidents/{identity}/decision", status_code=501, responses=UNAVAILABLE_RESPONSES)
@router.post("/incidents/{identity}/apply", status_code=501, responses=UNAVAILABLE_RESPONSES)
@router.post("/incidents/{identity}/runs", status_code=501, responses=UNAVAILABLE_RESPONSES)
@router.post(
    "/applications/{identity}/monitoring/start", status_code=501, responses=UNAVAILABLE_RESPONSES
)
@router.post(
    "/applications/{identity}/monitoring/stop", status_code=501, responses=UNAVAILABLE_RESPONSES
)
def unavailable(identity: schemas.Identifier) -> None:
    """Compatibility guard: no decision, execution, monitoring or settings mutation."""
    raise ApiError(
        501,
        "NOT_IMPLEMENTED",
        "This backend phase is read-only. Workflow and control mutations are not implemented.",
    )


@router.patch("/settings", status_code=501, responses=UNAVAILABLE_RESPONSES)
def unavailable_settings() -> None:
    """Safe settings remain read-only in this phase."""
    raise ApiError(501, "NOT_IMPLEMENTED", "Backend settings writes are not implemented.")
