"""Agent protocol definitions and registry."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    OFFLINE = "offline"


class AgentType(str, Enum):
    MANAGER = "manager"
    MONITORING = "monitoring"
    DIAGNOSIS = "diagnosis"
    REPAIR = "repair"
    TESTING = "testing"
    REPORTING = "reporting"


@dataclass
class AgentInput:
    incident_id: str
    run_id: str
    repository_revision: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0


class AgentProtocol(ABC):
    """Base protocol all agents must implement."""

    agent_type: AgentType
    name: str
    owner: str
    responsibility: str
    inputs: list[str]
    outputs: list[str]
    timeout_seconds: int = 120

    # Runtime state (not persisted directly ? use DB)
    _status: AgentStatus = AgentStatus.IDLE
    _current_task: str | None = None
    _last_activity: str | None = None

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def current_task(self) -> str | None:
        return self._current_task

    @property
    def last_activity(self) -> str | None:
        return self._last_activity

    @abstractmethod
    async def execute(self, inp: AgentInput) -> AgentOutput:
        """Execute the agent and return structured output."""

    def to_summary(self) -> dict[str, Any]:
        return {
            "agent_type": self.agent_type.value,
            "name": self.name,
            "status": self._status.value,
            "responsibility": self.responsibility,
            "owner": self.owner,
            "current_task": self._current_task,
            "last_activity": self._last_activity,
        }

    def to_detail(self, recent_runs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {
            **self.to_summary(),
            "inputs": self.inputs,
            "outputs": self.outputs,
            "recent_runs": recent_runs or [],
        }


# ?? STUB IMPLEMENTATIONS ??????????????????????????????????????????????????????
# These are clearly-labeled development stubs behind the agent interfaces.
# They are NOT functioning AI agents. Each team member should replace their
# stub with a real implementation.

class _StubAgent(AgentProtocol):
    """Base stub ? returns placeholder data with an honest stub label."""

    is_stub: bool = True

    async def execute(self, inp: AgentInput) -> AgentOutput:
        self._status = AgentStatus.RUNNING
        self._current_task = f"[STUB] Processing {inp.incident_id}"
        try:
            result = await self._stub_execute(inp)
            self._status = AgentStatus.COMPLETED
            self._last_activity = f"[STUB] Completed for {inp.incident_id} at {datetime.now(UTC).isoformat()}"
            return result
        except Exception as exc:
            self._status = AgentStatus.ERROR
            self._last_activity = f"[STUB] Error for {inp.incident_id}: {exc}"
            return AgentOutput(success=False, error=str(exc))
        finally:
            self._current_task = None

    async def _stub_execute(self, inp: AgentInput) -> AgentOutput:
        raise NotImplementedError


class MonitoringAgentStub(_StubAgent):
    """STUB ? Neha's Monitoring Agent. Not implemented yet."""

    agent_type = AgentType.MONITORING
    name = "Monitoring Agent"
    owner = "Neha"
    responsibility = "Spots supported failures in the designated sample application."
    inputs = ["Allowlisted sample logs"]
    outputs = ["Sanitized, deduplicated incident events"]

    async def _stub_execute(self, inp: AgentInput) -> AgentOutput:
        # Stub: returns a simulated detected incident
        return AgentOutput(
            success=True,
            data={
                "stub": True,
                "message": "Monitoring stub ? replace with Neha's implementation.",
                "detected_error_type": "NullReferenceError",
                "sanitized_message": "Registration fails on missing profile [STUB]",
            },
        )


class DiagnosisAgentStub(_StubAgent):
    """STUB ? Sahad's Diagnosis Agent + Code RAG. Not implemented yet."""

    agent_type = AgentType.DIAGNOSIS
    name = "Diagnosis Agent"
    owner = "Sahad"
    responsibility = "Connects errors to revision-bound code evidence with Code RAG."
    inputs = ["Error context, exact repository revision"]
    outputs = ["Cited hypothesis, uncertainty, suggested direction"]

    async def _stub_execute(self, inp: AgentInput) -> AgentOutput:
        return AgentOutput(
            success=True,
            data={
                "stub": True,
                "status": "completed",
                "hypothesis": "[STUB] Registration handler accesses profile before null check. Replace with Sahad's Code RAG implementation.",
                "confidence_label": "low",
                "uncertainty": "STUB output ? evidence not retrieved from real code index.",
                "suggested_direction": "Add null guard before profile access.",
                "evidence": [
                    {
                        "file_path": "src/registration.py",
                        "symbol": "register_user",
                        "start_line": 42,
                        "end_line": 49,
                        "repository_revision": inp.repository_revision,
                        "artifact_id": f"stub_art_{inp.incident_id}",
                        "excerpt": '[STUB] name = payload["profile"]["name"]',
                    }
                ],
            },
        )


class RepairAgentStub(_StubAgent):
    """STUB ? Yadhulakshmi's Repair Agent. Not implemented yet."""

    agent_type = AgentType.REPAIR
    name = "Repair Agent"
    owner = "Yadhulakshmi"
    responsibility = "Proposes focused, reviewable patches with a clear rationale."
    inputs = ["Diagnosis evidence, source revision"]
    outputs = ["Immutable patch candidate, diff, hash"]

    async def _stub_execute(self, inp: AgentInput) -> AgentOutput:
        import hashlib

        diff = (
            "--- a/src/registration.py\n"
            "+++ b/src/registration.py\n"
            "@@ -8,7 +8,8 @@\n"
            " def register_user(payload: dict) -> dict:\n"
            '     """Register a user. BUG: does not guard against missing profile."""\n'
            "     # BUG: This line will raise KeyError/AttributeError when profile is None\n"
            '-    name = payload["profile"]["name"]\n'
            '+    profile = payload.get("profile") or {}\n'
            '+    name = profile.get("name", "Guest")\n'
            "     return create_user(name)\n"
        )
        normalized = diff.replace("\r\n", "\n").strip()
        patch_hash = "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return AgentOutput(
            success=True,
            data={
                "stub": True,
                "diff": diff,
                "patch_hash": patch_hash,
                "changed_files": ["src/registration.py"],
                "rationale": "[STUB] Guard missing profile. Replace with Yadhulakshmi's implementation.",
                "base_revision": inp.repository_revision,
            },
        )


class TestingAgentStub(_StubAgent):
    """STUB ? Sravan's Testing Agent. Not implemented yet."""

    agent_type = AgentType.TESTING
    name = "Testing Agent"
    owner = "Sravan"
    responsibility = "Validates candidates in isolation before human review."
    inputs = ["Exact patch candidate, reproduction fixture"]
    outputs = ["Check results, test evidence, verification"]

    async def _stub_execute(self, inp: AgentInput) -> AgentOutput:
        candidate_id = inp.extra.get("candidate_id", "unknown")
        return AgentOutput(
            success=True,
            data={
                "stub": True,
                "status": "passed",
                "checks": [
                    {
                        "name": "registration_reproduction",
                        "status": "passed",
                        "exit_code": 0,
                        "duration_ms": 410,
                        "evidence_artifact_id": f"stub_test_{candidate_id}_0",
                        "evidence": "[STUB] Simulated reproduction check passed. Replace with Sravan's isolated runner.",
                    },
                    {
                        "name": "existing_profile_smoke",
                        "status": "passed",
                        "exit_code": 0,
                        "duration_ms": 180,
                        "evidence_artifact_id": f"stub_test_{candidate_id}_1",
                        "evidence": "[STUB] Simulated smoke test passed.",
                    },
                ],
                "environment_id": f"stub_sandbox_{candidate_id}",
                "duration_ms": 590,
            },
        )


class ReportingAgentStub(_StubAgent):
    """STUB ? Neha's Reporting Agent. Not implemented yet."""

    agent_type = AgentType.REPORTING
    name = "Reporting Agent"
    owner = "Neha"
    responsibility = "Turns the incident journey into a clear, evidence-led report."
    inputs = ["Persisted decisions and verification results"]
    outputs = ["Outcome report, limitations, audit summary"]

    async def _stub_execute(self, inp: AgentInput) -> AgentOutput:
        outcome = inp.extra.get("outcome", "reported")
        return AgentOutput(
            success=True,
            data={
                "stub": True,
                "summary": f"[STUB] Report for {inp.incident_id}: outcome={outcome}. Replace with Neha's template engine.",
                "outcome": outcome,
                "limitations": [
                    "STUB report ? no real evidence gathered.",
                    "Replace with Neha's Reporting Agent implementation.",
                ],
            },
        )


# ?? Registry ??????????????????????????????????????????????????????????????????

class AgentRegistry:
    """Central registry and dispatcher for all agents."""

    def __init__(self) -> None:
        self._agents: dict[AgentType, AgentProtocol] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for agent in [
            MonitoringAgentStub(),
            DiagnosisAgentStub(),
            RepairAgentStub(),
            TestingAgentStub(),
            ReportingAgentStub(),
        ]:
            self._agents[agent.agent_type] = agent

    def register(self, agent: AgentProtocol) -> None:
        """Replace stub with a real implementation."""
        self._agents[agent.agent_type] = agent

    def get(self, agent_type: AgentType) -> AgentProtocol:
        return self._agents[agent_type]

    def all(self) -> list[AgentProtocol]:
        return list(self._agents.values())

    async def dispatch(self, agent_type: AgentType, inp: AgentInput) -> AgentOutput:
        agent = self.get(agent_type)
        return await agent.execute(inp)


# Singleton registry
_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
