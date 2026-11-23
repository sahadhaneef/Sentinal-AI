from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app import models as M
from app.db.types import UTCDateTime
from tests.database.conftest import DOMAIN_TABLES


def test_migration_creates_all_expected_tables_and_relationships(graph):
    assert set(inspect(graph).get_table_names()) == DOMAIN_TABLES | {"alembic_version"}
    with Session(graph) as session:
        user = session.get(M.User, "reviewer")
        assert [role.name for role in user.roles] == ["reviewer"]
        assert len(user.sessions) == 1
        app = session.get(M.Application, "app_demo")
        assert app.revision_selection.revision.revision == "demoabc"
        assert len(app.revisions) == 1
        run = session.get(M.WorkflowRun, "run_001")
        assert len(run.executions) == 6
        assert len(run.transitions) == 1
        assert len(run.incident.monitoring_events) == 1
        diagnosis = session.get(M.Diagnosis, "diagnosis_001")
        assert diagnosis.evidence[0].source.file_path == "src/registration.py"
        assert diagnosis.evidence[0].source.artifact.storage_key == "fixtures/source.txt"
        patch = session.get(M.PatchCandidate, "patch_001")
        assert patch.run.id == run.id
        assert patch.diff_artifact.kind == "diff"
        assert patch.validations[0].checks[0].exit_code == 0
        attempt = session.get(M.ApplicationAttempt, "attempt_001")
        assert attempt.approval.actor.id == user.id
        assert attempt.approval.validation.candidate.id == patch.id
        assert attempt.verifications[0].checks[0].status == "failed"
        report = session.scalar(select(M.IncidentReport))
        assert report.incident.status == report.outcome == "unresolved"
        assert session.scalar(select(M.AuditEvent)).incident.id == run.incident_id
        assert session.scalar(select(M.AuthSession)).user.id == user.id


def test_ids_utc_and_schema_versions_round_trip(graph):
    with Session(graph) as session:
        user = session.get(M.User, "reviewer")
        assert user.created_at.tzinfo == UTC
        assert user.updated_at.tzinfo == UTC
        assert user.schema_version == "1.0"
        assert session.scalar(select(M.Incident)).detected_at.tzinfo == UTC
        generated = session.scalar(select(M.UserRole)).id
        from uuid import UUID

        assert str(UUID(generated)) == generated


def test_aware_timestamps_normalize_and_naive_timestamps_fail():
    value = datetime(2026, 11, 18, 12, tzinfo=timezone(timedelta(hours=2)))
    storage = UTCDateTime().process_bind_param(value, None)
    assert storage == datetime(2026, 11, 18, 10)
    assert UTCDateTime().process_result_value(storage, None).tzinfo == UTC
    with pytest.raises(ValueError, match="aware"):
        UTCDateTime().process_bind_param(datetime(2026, 11, 18), None)


def test_database_reports_no_foreign_key_or_integrity_errors(graph):
    with graph.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
        assert connection.scalar(text("PRAGMA integrity_check")) == "ok"
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1


def test_important_partial_and_lookup_indexes_exist(database):
    inspector = inspect(database)
    assert {i["name"] for i in inspector.get_indexes("incidents")} >= {
        "uq_incidents_active_fingerprint",
        "ix_incidents_application_status_detected",
    }
    assert any(i["unique"] for i in inspector.get_indexes("workflow_runs"))
