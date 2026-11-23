"""Explicit model registration; importing never creates tables or runs agents."""

from app.models.application import (
    Application,
    ApplicationRevision,
    Artifact,
    BackendSettings,
    CodeIndexEntry,
    RepositoryRevision,
)
from app.models.audit import AuditEvent, IdempotencyRecord
from app.models.diagnosis import Diagnosis, EvidenceReference
from app.models.identity import AuthSession, Role, User, UserRole
from app.models.incident import Incident, IncidentMonitoringEvent, MonitoringEvent
from app.models.outcome import (
    ApplicationAttempt,
    IncidentReport,
    VerificationCheck,
    VerificationResult,
)
from app.models.repair import ApprovalDecision, PatchCandidate, ValidationCheck, ValidationResult
from app.models.workflow import AgentExecution, StageTransition, WorkflowRun

__all__ = [
    "AgentExecution",
    "Application",
    "ApplicationAttempt",
    "ApplicationRevision",
    "ApprovalDecision",
    "Artifact",
    "AuditEvent",
    "AuthSession",
    "BackendSettings",
    "CodeIndexEntry",
    "Diagnosis",
    "EvidenceReference",
    "IdempotencyRecord",
    "Incident",
    "IncidentMonitoringEvent",
    "IncidentReport",
    "MonitoringEvent",
    "PatchCandidate",
    "RepositoryRevision",
    "Role",
    "StageTransition",
    "User",
    "UserRole",
    "ValidationCheck",
    "ValidationResult",
    "VerificationCheck",
    "VerificationResult",
    "WorkflowRun",
]
