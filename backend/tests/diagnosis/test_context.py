"""Incident/log linkage and source revision policy preserve existing domain ownership."""

from collections.abc import Sequence

import pytest

from app.agents.diagnosis.code_rag.contracts import RetrievalRequest
from app.agents.diagnosis.code_rag.hashing import digest
from app.db.types import utc_now
from app.models import Artifact, WorkflowRun
from app.models.enums import RunState
from app.repositories.incident import MonitoringInput
from app.repositories.unit_of_work import transaction
from tests.diagnosis.conftest import Harness


def test_linked_log_reference_and_incident_run_scope(harness: Harness) -> None:
    (harness.root / "app.py").write_bytes(b'def register(profile):\n    return profile["name"]\n')
    harness.service.index("rag_app", "r1")
    log = b'File "app.py", line 2, in register\nKeyError: name'
    harness.settings.artifact_root.mkdir(parents=True, exist_ok=True)
    (harness.settings.artifact_root / "log.txt").write_bytes(log)
    with transaction(harness.engine) as store:
        store.records(Artifact).add(
            Artifact(
                id="linked_log",
                kind="log",
                storage_key="log.txt",
                sha256=digest(log),
                size_bytes=len(log),
                content_type="text/plain",
                redacted=True,
            )
        )
        _, incident = store.incidents.record_monitoring_event(
            MonitoringInput(
                application_id="rag_app",
                repository_revision="r1",
                source_event_id="event1",
                fingerprint=digest(b"incident"),
                severity="high",
                error_type="KeyError",
                message="name",
                occurred_at=utc_now(),
                log_artifact_id="linked_log",
            )
        )
        store.records(WorkflowRun).add(
            WorkflowRun(
                id="rag_run",
                incident_id=incident.id,
                application_id="rag_app",
                repository_revision="r1",
                state=RunState.DETECTED,
            )
        )
    request = RetrievalRequest(
        application_id="rag_app",
        repository_revision="r1",
        incident_id=incident.id,
        run_id="rag_run",
        stack_trace_ref="linked_log",
    )
    result = harness.service.retrieve(request)
    assert result.status == "ready" and result.evidence[0].exact_tier == 2
    harness.register("r1", "other", "other")
    invalid = harness.service.retrieve(request.model_copy(update={"application_id": "other"}))
    assert invalid.status == "unavailable" and invalid.reason == "SCOPE_MISMATCH"
    unlinked = harness.service.retrieve(
        request.model_copy(
            update={
                "application_id": "other",
                "incident_id": None,
                "run_id": None,
            }
        )
    )
    assert unlinked.status == "unavailable"


def test_unlinked_log_not_accepted(harness: Harness) -> None:
    harness.service.index("rag_app", "r1")
    request = RetrievalRequest(
        application_id="rag_app", repository_revision="r1", stack_trace_ref="not_linked"
    )
    result = harness.service.retrieve(request)
    assert result.status == "unavailable" and result.reason == "LOG_SCOPE"


def test_crlf_source_bytes_are_preserved(harness: Harness) -> None:
    source = b"def profile():\r\n    return 1\r\n"
    (harness.root / "app.py").write_bytes(source)
    harness.service.index("rag_app", "r1")
    request = RetrievalRequest(
        application_id="rag_app", repository_revision="r1", search_query="profile"
    )
    result = harness.service.retrieve(request)
    assert result.evidence[0].excerpt.encode() == source


def test_source_mutation_during_embedding_is_not_published(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = harness.root / "app.py"
    file.write_bytes(b"profile = 1\n")
    original = harness.encoder.documents

    def mutate(texts: Sequence[str]) -> list[list[float]]:
        file.write_bytes(b"profile = 2\n")
        return original(texts)

    monkeypatch.setattr(harness.encoder, "documents", mutate)
    from app.agents.diagnosis.code_rag.errors import SourceRejected

    with pytest.raises(SourceRejected, match="changed during indexing"):
        harness.service.index("rag_app", "r1")
