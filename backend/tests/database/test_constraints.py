from datetime import datetime

import pytest
from sqlalchemy import text

from app import models as M
from app.models.enums import RunState
from app.repositories import transaction
from app.repositories.errors import Conflict, InvalidRecord
from tests.database.conftest import HASH, HASH2
from tests.database.helpers import event


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("incidents", "status", "validation_failed"),
        ("incidents", "severity", "extreme"),
        ("workflow_runs", "state", "repairing"),
        ("agent_executions", "agent_type", "approval_agent"),
        ("agent_executions", "status", "pretending"),
        ("patch_candidates", "status", "unknown"),
        ("validation_results", "status", "skipped"),
        ("verification_results", "status", "success"),
        ("application_attempts", "restore_status", "deployed"),
        ("applications", "status", "operational"),
        ("diagnoses", "confidence_label", "certain"),
    ],
)
def test_sql_bypass_still_rejects_invalid_status_enums(graph, table, column, value):
    # Identifiers come only from this fixed test matrix, never request data.
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(text(f'UPDATE "{table}" SET "{column}" = :value'), {"value": value})


@pytest.mark.parametrize(
    "changes",
    [
        {"application_id": "missing"},
        {"repository_revision": "missing"},
        {"log_artifact_id": "missing"},
    ],
)
def test_monitoring_foreign_keys_are_real(minimal, changes):
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.incidents.record_monitoring_event(event(**changes))


@pytest.mark.parametrize(
    "key",
    [
        "../private",
        "/absolute/path",
        "C:/private",
        "logs/../../secret",
        "logs/%2e%2e/secret",
        "logs\\secret",
    ],
)
def test_unsafe_artifact_keys_are_rejected(minimal, key):
    with pytest.raises(InvalidRecord), transaction(minimal) as store:
        store.records(M.Artifact).add(
            M.Artifact(
                kind="log",
                storage_key=key,
                sha256=HASH,
                size_bytes=10,
                content_type="text/plain",
                redacted=True,
            )
        )


def test_sql_bypass_cannot_store_traversal_or_malformed_digests(minimal):
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.session.execute(
            text("UPDATE artifacts SET storage_key='../secret' WHERE id='art_log'")
        )
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.session.execute(text("UPDATE artifacts SET sha256='not-a-digest' WHERE id='art_log'"))


def test_naive_datetime_rejected_on_actual_database_write(minimal):
    with pytest.raises(InvalidRecord), transaction(minimal) as store:
        store.users.add(
            M.User(username="naive", display_name="Fixture", created_at=datetime(2026, 1, 1))
        )


def test_missing_and_cross_application_revision_references_fail(graph):
    with pytest.raises(Conflict), transaction(graph) as store:
        store.records(M.RepositoryRevision).add(
            M.RepositoryRevision(
                application_id="missing",
                revision="abc",
                snapshot_artifact_id="art_snapshot",
            )
        )
    with pytest.raises(Conflict), transaction(graph) as store:
        store.applications.add(M.Application(id="other", name="Other", workspace_key="other"))
        store.records(M.ApplicationRevision).add(
            M.ApplicationRevision(
                application_id="other",
                revision_id="revision_001",
            )
        )


def test_evidence_cannot_cite_another_revision(graph):
    with transaction(graph) as store:
        store.records(M.RepositoryRevision).add(
            M.RepositoryRevision(
                application_id="app_demo",
                revision="another",
                snapshot_artifact_id="art_snapshot",
            )
        )
        store.records(M.CodeIndexEntry).add(
            M.CodeIndexEntry(
                id="other_code",
                application_id="app_demo",
                repository_revision="another",
                file_path="src/other.py",
                symbol="other",
                start_line=1,
                end_line=2,
                content_hash=HASH,
                artifact_id="art_source",
            )
        )
    with pytest.raises(Conflict), transaction(graph) as store:
        store.records(M.EvidenceReference).add(
            M.EvidenceReference(
                diagnosis_id="diagnosis_001",
                code_index_entry_id="other_code",
                application_id="app_demo",
                repository_revision="demoabc",
            )
        )


def test_a_second_active_run_and_conflicting_application_are_rejected(minimal):
    with transaction(minimal) as store:
        _, incident = store.incidents.record_monitoring_event(event())
        incident_id = incident.id
        store.records(M.WorkflowRun).add(
            M.WorkflowRun(
                incident_id=incident_id,
                application_id="app_demo",
                repository_revision="demoabc",
                attempt=1,
                state=RunState.APPLYING,
            )
        )
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.records(M.WorkflowRun).add(
            M.WorkflowRun(
                incident_id=incident_id,
                application_id="app_demo",
                repository_revision="demoabc",
                attempt=2,
            )
        )
    with pytest.raises(Conflict), transaction(minimal) as store:
        _, different = store.incidents.record_monitoring_event(
            event(
                source_event_id="different",
                fingerprint=HASH2,
            )
        )
        store.records(M.WorkflowRun).add(
            M.WorkflowRun(
                incident_id=different.id,
                application_id="app_demo",
                repository_revision="demoabc",
                state=RunState.APPLYING,
            )
        )


def test_approval_requires_exact_candidate_hash_and_passing_validation(graph):
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(
            text("UPDATE approval_decisions SET patch_hash=:hash"), {"hash": HASH2}
        )
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(text("UPDATE approval_decisions SET validation_status='failed'"))
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(
            text("UPDATE approval_decisions SET validation_id=NULL, validation_status=NULL")
        )


def test_a_passed_check_must_have_an_actual_zero_exit_code(graph):
    for exit_code in (None, 1):
        with pytest.raises(Conflict), transaction(graph) as store:
            store.session.execute(
                text("UPDATE validation_checks SET exit_code=:code"), {"code": exit_code}
            )


def test_application_record_cannot_be_backed_by_a_rejection(graph):
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(text("UPDATE application_attempts SET approval_decision='reject'"))
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(text("UPDATE approval_decisions SET decision='reject'"))


def test_attempt_and_verification_cannot_change_candidate_identity(graph):
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(text("UPDATE verification_results SET candidate_id='different'"))
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(text("UPDATE application_attempts SET before_revision='different'"))


def test_referenced_users_and_applications_cannot_be_deleted(graph):
    with pytest.raises(Conflict), transaction(graph) as store:
        store.users.delete("reviewer")
    with pytest.raises(Conflict), transaction(graph) as store:
        store.applications.delete("app_demo")


def test_direct_duplicate_active_incident_is_blocked_even_without_repository_upsert(minimal):
    with transaction(minimal) as store:
        _, original = store.incidents.record_monitoring_event(event())
        values = {
            field: getattr(original, field)
            for field in [
                "application_id",
                "repository_revision",
                "source_event_id",
                "fingerprint",
                "severity",
                "error_type",
                "message",
            ]
        }
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.records(M.Incident).add(M.Incident(**values))


@pytest.mark.parametrize(
    "table,assignment",
    [
        ("backend_settings", "monitoring_interval_seconds=0"),
        ("backend_settings", "max_candidate_revisions=3"),
        ("artifacts", "size_bytes=-1"),
        ("artifacts", "redacted=2"),
        ("code_index_entries", "end_line=0"),
        ("validation_checks", "duration_ms=-1"),
        ("stage_transitions", "sequence=0"),
        ("auth_sessions", "expires_at=created_at"),
    ],
)
def test_numeric_and_timestamp_bounds_are_database_constraints(graph, table, assignment):
    with pytest.raises(Conflict), transaction(graph) as store:
        store.session.execute(text(f'UPDATE "{table}" SET {assignment}'))


@pytest.mark.parametrize("metadata", [{"payload": "x" * 16385}, [float("nan")], "text"])
def test_large_or_invalid_metadata_requires_external_artifacts(minimal, metadata):
    with pytest.raises(InvalidRecord), transaction(minimal) as store:
        store.applications.update("app_demo", supported_errors=metadata)


@pytest.mark.parametrize("files", [[], ["../secret"], ["src/a.py", "src/a.py"]])
def test_invalid_candidate_file_lists_are_rejected(graph, files):
    with pytest.raises(InvalidRecord), transaction(graph) as store:
        candidate = store.patches.get("patch_001")
        # Exercise bind validation directly; supported repository updates are immutable.
        candidate.changed_files = files
        store.session.flush()


def test_workspace_revision_and_candidate_versions_are_unique(graph):
    with pytest.raises(Conflict), transaction(graph) as store:
        store.applications.add(M.Application(name="Duplicate", workspace_key="demo"))
    with pytest.raises(Conflict), transaction(graph) as store:
        store.records(M.RepositoryRevision).add(
            M.RepositoryRevision(
                application_id="app_demo", revision="demoabc", snapshot_artifact_id="art_snapshot"
            )
        )
    with pytest.raises(Conflict), transaction(graph) as store:
        original = store.patches.get("patch_001")
        fields = (
            "incident_id",
            "run_id",
            "application_id",
            "version",
            "base_revision",
            "patch_hash",
            "changed_files",
            "rationale",
            "diff_artifact_id",
        )
        store.patches.add(M.PatchCandidate(**{key: getattr(original, key) for key in fields}))
