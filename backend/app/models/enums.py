from enum import StrEnum

from sqlalchemy import Enum


class RunState(StrEnum):
    DETECTED = "detected"
    DIAGNOSING = "diagnosing"
    GENERATING_PATCH = "generating_patch"
    VALIDATING = "validating"
    REVISION_REQUESTED = "revision_requested"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    APPLYING = "applying"
    VERIFYING = "verifying"
    RESTORING = "restoring"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    UNRESOLVED = "unresolved"
    ERROR = "error"
    REPORTED = "reported"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentType(StrEnum):
    MANAGER = "manager"
    MONITORING = "monitoring"
    DIAGNOSIS = "diagnosis"
    REPAIR = "repair"
    TESTING = "testing"
    REPORTING = "reporting"


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    OFFLINE = "offline"


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    NOT_RUN = "not_run"


class PatchStatus(StrEnum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    FAILED = "failed"
    STALE = "stale"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


def status_type(enum: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [item.value for item in values],
    )


INCIDENT_CLOSED = ("resolved", "rejected", "unresolved", "reported")
RUN_TERMINAL = (*INCIDENT_CLOSED, "manual_review", "error")
