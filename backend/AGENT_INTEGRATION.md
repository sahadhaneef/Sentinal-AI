# SENTINEL AI ? Agent Integration Guide

## Team Responsibilities

| Member | Agent / Component | Status in Codebase |
|---|---|---|
| **Delvin** | **Manager Agent, Shared Backend, DB, State Machine, Apply & Integration** | **Complete & Tested** |
| **Sahad** | **Diagnosis Agent & Code RAG** | Interface Defined / Development Stub |
| **Yadhulakshmi** | **Repair Agent** | Interface Defined / Development Stub |
| **Neha** | **Monitoring Agent & Reporting Agent** | Interface Defined / Development Stub |
| **Sravan** | **Testing Agent** | Interface Defined / Development Stub |

---

## Standard Agent Protocol

All agents implement the standard `AgentProtocol` abstract class defined in `backend/app/agents/registry.py`:

```python
from app.agents.registry import AgentProtocol, AgentType, AgentInput, AgentOutput

class MyAgent(AgentProtocol):
    agent_type = AgentType.DIAGNOSIS # or MONITORING, REPAIR, TESTING, REPORTING
    name = "Diagnosis Agent"
    owner = "Sahad"
    responsibility = "Connects errors to revision-bound code evidence with Code RAG."
    inputs = ["Error context, exact repository revision"]
    outputs = ["Cited hypothesis, uncertainty, suggested direction"]
    timeout_seconds = 120

    async def execute(self, inp: AgentInput) -> AgentOutput:
        # inp.incident_id: ID of the incident
        # inp.run_id: current active run ID
        # inp.repository_revision: application revision at time of detection
        # inp.extra: contextual dictionary (e.g. candidate_id, outcome, etc.)
        
        # Return structured AgentOutput
        return AgentOutput(
            success=True,
            data={ ... },
            duration_ms=450
        )
```

---

## How Teammates Plug In Their Agent

To replace a development stub with your completed module:

1. Place your agent implementation in `backend/app/agents/<your_agent>/`.
2. Implement `AgentProtocol`.
3. In `backend/app/agents/registry.py`:
   ```python
   from .my_agent import MyAgent
   
   registry = get_registry()
   registry.register(MyAgent())
   ```
4. The Manager Agent will automatically dispatch to your agent at the appropriate workflow stage!

---

## Specific Handoff Contracts

### 1. Sahad ? Diagnosis Agent (`AgentType.DIAGNOSIS`)
- **Input (`inp`)**:
  - `inp.incident_id`: Unique incident ID (e.g. `inc_001`).
  - `inp.run_id`: Active workflow run ID.
  - `inp.repository_revision`: Exact Git revision of the application when failure occurred.
  - `inp.extra["source_log"]`: Redacted stack trace/log snippet.
  - `inp.extra["error_type"]`: Classified error name (e.g. `NullReferenceError`, `ZeroDivisionError`).
  - `inp.extra["error_message"]`: High-level error description.
  - `inp.extra["application_id"]`: Application identifier (`app_demo`).
- **Output `data` schema**:
  ```json
  {
    "status": "completed", // or "manual_review" if no evidence / uncertain
    "hypothesis": "Root cause explanation",
    "confidence_label": "low" | "medium" | "high",
    "uncertainty": "Boundaries and limitations of hypothesis",
    "suggested_direction": "Recommended direction for repair",
    "evidence": [
      {
        "file_path": "src/registration.py",
        "symbol": "register_user",
        "start_line": 8,
        "end_line": 13,
        "repository_revision": "abc123",
        "artifact_id": "art_code_001",
        "excerpt": "name = payload[\"profile\"][\"name\"]"
      }
    ]
  }
  ```
  *(Note: The Manager Agent also automatically accepts alias fields `root_cause`, `suggested_fix`, and `affected_files` without error).*

### 2. Yadhulakshmi ? Repair Agent (`AgentType.REPAIR`)
- **Input**:
  - `inp.incident_id`
  - `inp.repository_revision`
- **Output `data` schema**:
  ```json
  {
    "diff": "--- a/src/registration.py\n+++ b/src/registration.py\n...",
    "patch_hash": "sha256:<sha256-hex-of-diff>",
    "changed_files": ["src/registration.py"],
    "rationale": "Guard null profile before accessing name",
    "base_revision": "abc123"
  }
  ```

### 3. Sravan ? Testing Agent (`AgentType.TESTING`)
- **Input**:
  - `inp.incident_id`
  - `inp.extra["candidate_id"]`
  - `inp.extra["patch_hash"]`
- **Output `data` schema**:
  ```json
  {
    "status": "passed", // or "failed"
    "checks": [
      {
        "name": "registration_reproduction",
        "status": "passed",
        "exit_code": 0,
        "duration_ms": 320,
        "evidence_artifact_id": "art_test_01",
        "evidence": "Reproduction test output"
      }
    ],
    "environment_id": "isolated_sandbox",
    "duration_ms": 500
  }
  ```

### 4. Neha ? Monitoring & Reporting (`AgentType.MONITORING` & `AgentType.REPORTING`)
- **Reporting Agent output `data` schema**:
  ```json
  {
    "summary": "Full incident summary narrative",
    "outcome": "resolved" | "rejected" | "unresolved",
    "limitations": [
      "Simulated reproduction only",
      "No production deployment attempted"
    ]
  }
  ```
