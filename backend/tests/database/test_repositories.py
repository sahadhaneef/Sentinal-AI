from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as M
from app.models.enums import RunState
from app.repositories import transaction
from app.repositories.errors import Conflict, ImmutableRecord, InvalidRecord, NotFound
from tests.database.conftest import HASH, HASH2
from tests.database.helpers import event


def count(engine, model) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(model))


def test_crud_and_commit_across_sessions(database):
    with transaction(database) as store:
        user = store.users.add(M.User(username="alice", display_name="Alice"))
        identity = user.id
    with transaction(database) as store:
        assert store.users.get(identity).display_name == "Alice"
        assert [row.id for row in store.users.list(limit=1)] == [identity]
        store.users.update(identity, display_name="Updated")
    with transaction(database) as store:
        assert store.users.get(identity).display_name == "Updated"
        store.users.delete(identity)
    with transaction(database) as store, pytest.raises(NotFound):
        store.users.get(identity)


def test_a_late_failure_rolls_back_every_earlier_write(database):
    with pytest.raises(Conflict) as failure, transaction(database) as store:
        store.users.add(M.User(username="same", display_name="First"))
        store.users.add(M.User(username="SAME", display_name="Duplicate"))
    assert "INSERT" not in str(failure.value)
    assert count(database, M.User) == 0
    with transaction(database) as store:
        store.users.add(M.User(username="after-rollback", display_name="Healthy"))
    assert count(database, M.User) == 1


def test_non_database_failure_rolls_back_transaction(database):
    with pytest.raises(RuntimeError), transaction(database) as store:
        store.users.add(M.User(username="rolled-back", display_name="Fixture"))
        raise RuntimeError("Abort the operation")
    assert count(database, M.User) == 0


@pytest.mark.parametrize("limit,offset", [(0, 0), (101, 0), (True, 0), (10, -1), ("10", 0)])
def test_repository_rejects_bad_pagination(database, limit, offset):
    with transaction(database) as store, pytest.raises(InvalidRecord):
        store.users.list(limit=limit, offset=offset)


def test_exact_replay_and_repeated_fingerprint_deduplicate_without_starting_runs(minimal):
    with transaction(minimal) as store:
        original_event, original_incident = store.incidents.record_monitoring_event(event())
        original = (original_event.id, original_incident.id)
    with transaction(minimal) as store:
        replay_event, replay_incident = store.incidents.record_monitoring_event(event())
        assert (replay_event.id, replay_incident.id) == original
        next_event, same_incident = store.incidents.record_monitoring_event(
            event(source_event_id="event_002")
        )
        assert next_event.id != original[0]
        assert same_incident.id == original[1]
    assert count(minimal, M.MonitoringEvent) == 2
    assert count(minimal, M.Incident) == 1
    assert count(minimal, M.IncidentMonitoringEvent) == 2
    assert count(minimal, M.WorkflowRun) == 0


def test_replay_of_a_closed_event_does_not_reopen_it_but_new_event_can(minimal):
    with transaction(minimal) as store:
        _, incident = store.incidents.record_monitoring_event(event())
        old_id = incident.id
        store.incidents.update(old_id, status=RunState.REJECTED)
    with transaction(minimal) as store:
        _, replay = store.incidents.record_monitoring_event(event())
        assert replay.id == old_id
        assert replay.status == "rejected"
        _, new = store.incidents.record_monitoring_event(event(source_event_id="event_after_close"))
        assert new.id != old_id
    assert count(minimal, M.Incident) == 2


def test_source_id_reuse_for_different_content_is_a_conflict(minimal):
    with transaction(minimal) as store:
        store.incidents.record_monitoring_event(event())
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.users.add(M.User(username="must-rollback", display_name="Fixture"))
        store.incidents.record_monitoring_event(event(message="Changed evidence"))
    assert count(minimal, M.User) == 1
    assert count(minimal, M.MonitoringEvent) == 1


def test_an_active_incident_cannot_silently_absorb_a_different_revision(minimal):
    with transaction(minimal) as store:
        store.incidents.record_monitoring_event(event())
        store.records(M.RepositoryRevision).add(
            M.RepositoryRevision(
                application_id="app_demo",
                revision="newrevision",
                snapshot_artifact_id="art_snapshot",
            )
        )
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.incidents.record_monitoring_event(
            event(source_event_id="newrev_event", repository_revision="newrevision")
        )
    assert count(minimal, M.MonitoringEvent) == 1


@pytest.mark.parametrize("same_event", [True, False])
def test_concurrent_writers_cannot_create_duplicate_active_incidents(minimal, same_event):
    barrier = Barrier(2)

    def record(index):
        barrier.wait(timeout=5)
        with transaction(minimal) as store:
            _, incident = store.incidents.record_monitoring_event(
                event(source_event_id="concurrent" if same_event else f"concurrent_{index}")
            )
            return incident.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(record, index) for index in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert results[0] == results[1]
    assert count(minimal, M.Incident) == 1
    assert count(minimal, M.MonitoringEvent) == (1 if same_event else 2)


def test_candidate_revisions_keep_new_identity_and_immutable_previous_content(graph):
    with transaction(graph) as store:
        first = store.patches.get("patch_001")
        store.records(M.Artifact).add(
            M.Artifact(
                id="art_diff_2",
                kind="diff",
                storage_key="diffs/second.patch",
                sha256=HASH2,
                content_type="text/x-diff",
                size_bytes=42,
                redacted=True,
            )
        )
        second = store.patches.add(
            M.PatchCandidate(
                incident_id=first.incident_id,
                run_id=first.run_id,
                application_id=first.application_id,
                version=2,
                base_revision=first.base_revision,
                patch_hash=HASH2,
                changed_files=["src/registration.py"],
                rationale="New fixture candidate",
                diff_artifact_id="art_diff_2",
                supersedes_candidate_id=first.id,
            )
        )
        assert second.id != first.id
        assert second.predecessor.id == first.id
        assert first.patch_hash == HASH
        assert second.validations == []
        with pytest.raises(ImmutableRecord):
            store.patches.update(first.id, patch_hash=HASH2)


def test_candidate_artifact_hash_mismatch_is_not_registered(graph):
    with pytest.raises(Conflict), transaction(graph) as store:
        first = store.patches.get("patch_001")
        store.patches.add(
            M.PatchCandidate(
                incident_id=first.incident_id,
                run_id=first.run_id,
                application_id=first.application_id,
                version=2,
                base_revision=first.base_revision,
                patch_hash=HASH2,
                changed_files=["src/registration.py"],
                rationale="Mismatch",
                diff_artifact_id="art_diff",
                supersedes_candidate_id=first.id,
            )
        )
    assert count(graph, M.PatchCandidate) == 1


def test_historical_records_are_not_mutable_or_deletable_through_repositories(graph):
    with transaction(graph) as store:
        audit = store.records(M.AuditEvent).list()[0]
        with pytest.raises(ImmutableRecord):
            store.records(M.AuditEvent).update(audit.id, event_type="rewritten")
        with pytest.raises(ImmutableRecord):
            store.records(M.ApprovalDecision).delete("decision_001")


def test_unreferenced_roles_cascade_memberships_but_audited_users_are_restricted(minimal):
    with transaction(minimal) as store:
        store.records(M.Role).delete("role_reviewer")
    assert count(minimal, M.UserRole) == 0
    assert count(minimal, M.User) == 1


def test_revision_selection_checks_application_scope(minimal):
    with transaction(minimal) as store:
        store.applications.add(M.Application(id="other_app", name="Other", workspace_key="other"))
    with pytest.raises(Conflict), transaction(minimal) as store:
        store.applications.select_revision("other_app", "revision_001")
