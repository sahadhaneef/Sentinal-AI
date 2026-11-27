"""Verify trusted bytes and the actual supervisor-owned worker return path."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from time import monotonic
from unittest.mock import Mock

import pytest

from app.agents.diagnosis.execution.worker import IsolatedDiagnosisWorker
from app.agents.diagnosis.quality.trusted_contract import (
    InvocationContext,
    ManifestReadResult,
    RegisteredRevisionDTO,
    ScopedArtifactReadRequest,
    ScopedArtifactReadResult,
    SupervisedInvocation,
    read_verified_artifact,
    read_verified_manifest,
)
from tests.diagnosis.execution.helpers import FixtureFactory
from tests.diagnosis.reasoning.conftest import Scenario


@pytest.fixture
def invocation(scenario: Scenario) -> InvocationContext:
    return InvocationContext(
        **scenario.request.model_dump(
            include={"incident_id", "run_id", "application_id", "repository_revision"}
        ),
        execution_id="execution",
        repository_id="repo",
        revision_id="revision",
        snapshot_id="snapshot",
        invocation_id="invocation",
        attempt_number=1,
        idempotency_key="test-key",
        deadline_at=datetime.now(UTC) + timedelta(seconds=30),
    )


@pytest.mark.parametrize(
    "fault", [None, "scope", "revision", "missing", "bytes", "id", "digest", "size", "limit"]
)
def test_manifest_integrity(invocation: InvocationContext, fault: str | None) -> None:
    content = b'{ "snapshot": "snapshot" }\r\n'
    digest = sha256(content).hexdigest()
    registration = RegisteredRevisionDTO(
        application_id=invocation.application_id,
        repository_id=invocation.repository_id,
        revision_id=invocation.revision_id,
        revision=invocation.repository_revision,
        snapshot_id=invocation.snapshot_id,
        manifest_artifact_id="manifest",
        manifest_hash=digest,
    )
    result = ManifestReadResult(
        manifest_artifact_id="manifest",
        manifest_hash=digest,
        content_bytes=content,
        content_size=len(content),
    )
    revisions, reader = Mock(), Mock()
    revisions.resolve_registered_revision.return_value = registration.model_copy(
        update={
            **({"repository_id": "foreign"} if fault == "scope" else {}),
            **({"revision": "different"} if fault == "revision" else {}),
        }
    )
    if fault == "missing":
        revisions.resolve_registered_revision.side_effect = LookupError
    reader.read_registered_manifest.return_value = result.model_copy(
        update={
            **({"content_bytes": b"x" * len(content)} if fault == "bytes" else {}),
            **({"manifest_artifact_id": "other"} if fault == "id" else {}),
            **({"manifest_hash": "0" * 64} if fault == "digest" else {}),
            **({"content_size": 0} if fault == "size" else {}),
        }
    )
    limit = len(content) - (fault == "limit")
    if fault is None:
        assert read_verified_manifest(invocation, revisions, reader, max_bytes=limit) == content
    else:
        with pytest.raises((ValueError, LookupError)):
            read_verified_manifest(invocation, revisions, reader, max_bytes=limit)


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "application_id",
        "incident_id",
        "run_id",
        "execution_id",
        "revision_id",
        "missing",
        "denied",
        "bytes",
        "id",
        "size",
        "limit",
        "path",
    ],
)
def test_artifact_integrity(invocation: InvocationContext, fault: str | None) -> None:
    names = set(ScopedArtifactReadRequest.model_fields) - {"artifact_id", "max_bytes"}
    values = invocation.model_dump(include=names)
    if fault in names:
        values[fault] = "foreign"
    if fault == "path":
        with pytest.raises(ValueError):
            ScopedArtifactReadRequest(**values, artifact_id="../artifact", max_bytes=4)
        return
    request = ScopedArtifactReadRequest(
        **values, artifact_id="artifact", max_bytes=3 if fault == "limit" else 4
    )
    digest = sha256(b"test").hexdigest()
    reader = Mock()
    reader.read_scoped_artifact.return_value = ScopedArtifactReadResult(
        artifact_id="other" if fault == "id" else "artifact",
        content_hash=digest,
        content_bytes=b"fail" if fault == "bytes" else b"test",
        content_size=0 if fault == "size" else 4,
    )
    if fault in {"missing", "denied"}:
        reader.read_scoped_artifact.side_effect = (
            LookupError if fault == "missing" else PermissionError
        )
    if fault is None:
        assert (
            read_verified_artifact(invocation, request, reader, expected_sha256=digest) == b"test"
        )
    else:
        with pytest.raises((ValueError, LookupError, PermissionError)):
            read_verified_artifact(invocation, request, reader, expected_sha256=digest)
        if fault in names:
            reader.read_scoped_artifact.assert_not_called()


@pytest.mark.parametrize("current", [True, False])
async def test_supervised_worker_binds_one_actual_run(
    scenario: Scenario, invocation: InvocationContext, tmp_path: Path, current: bool
) -> None:
    state = Mock()
    state.is_current.side_effect = [True, current]
    supervisor = SupervisedInvocation(invocation, state)
    factory = FixtureFactory.for_scenario(scenario, tmp_path / "started")
    async with IsolatedDiagnosisWorker(factory) as worker:
        if current:
            bound, result = await supervisor.run(worker, deadline=monotonic() + 15)
            assert bound == invocation
            assert result.quality is not None
        else:
            with pytest.raises(ValueError, match="no longer active"):
                await supervisor.run(worker, deadline=monotonic() + 15)
        with pytest.raises(ValueError, match="already consumed"):
            await supervisor.run(worker, deadline=monotonic() + 15)


async def test_caller_assertions_cannot_supply_worker_output(
    invocation: InvocationContext,
) -> None:
    worker = Mock(spec=IsolatedDiagnosisWorker)
    supervisor = SupervisedInvocation(invocation, Mock())
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        await supervisor.run(
            worker,
            deadline=monotonic() + 15,
            origin=invocation,
            verified_manifest_hash="a" * 64,
        )
    worker.diagnose.assert_not_called()


@pytest.mark.parametrize("deadline_offset", [-1, 15])
async def test_inactive_or_expired_admission_never_starts_worker(
    invocation: InvocationContext, deadline_offset: int
) -> None:
    state = Mock()
    state.is_current.return_value = deadline_offset < 0
    worker = Mock(spec=IsolatedDiagnosisWorker)
    supervisor = SupervisedInvocation(invocation, state)
    with pytest.raises(ValueError, match="no longer active"):
        await supervisor.run(worker, deadline=monotonic() + deadline_offset)
    worker.diagnose.assert_not_called()
