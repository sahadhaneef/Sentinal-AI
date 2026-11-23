"""End-to-end persistent indexing, verified citations and honest degraded retrieval."""

import json
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text

from app.agents.diagnosis.code_rag.cache import Collection, Vector
from app.agents.diagnosis.code_rag.contracts import RetrievalRequest
from app.agents.diagnosis.code_rag.errors import IndexUnavailable, RevisionConflict, SourceRejected
from app.agents.diagnosis.code_rag.service import CodeRag
from app.agents.diagnosis.code_rag.stacktrace import hints, matching_path
from app.models import Artifact, CodeIndexEntry
from app.repositories.unit_of_work import transaction
from tests.diagnosis.conftest import Harness, TestEncoder

PROFILE = 'def registration(profile):\n    return profile["name"]\n'
PAYMENT = "def payment(database):\n    return database.charge()\n"


def write_sources(harness: Harness) -> None:
    (harness.root / "registration.py").write_bytes(PROFILE.encode())
    (harness.root / "payment.py").write_bytes(PAYMENT.encode())


def query(revision: str = "r1", **changes: object) -> RetrievalRequest:
    return RetrievalRequest.model_validate(
        dict(
            application_id="rag_app",
            repository_revision=revision,
            search_query="registration profile",
        )
        | changes
    )


def test_initial_idempotent_restart_and_resolvable_citations(harness: Harness) -> None:
    write_sources(harness)
    tables_before = set(inspect(harness.engine).get_table_names())
    before = harness.service.index("rag_app", "r1")
    assert before.files == before.chunks == before.embedded == 2
    after = harness.service.index("rag_app", "r1")
    assert after.embedded == 0 and after.cached == 2 and harness.encoder.calls == 2
    assert before.snapshot_hash == after.snapshot_hash
    restarted = CodeRag(harness.engine, harness.settings, harness.rag, TestEncoder())
    result = restarted.retrieve(query())
    assert result.status == "ready" and result.semantic_used
    assert result.evidence[0].file_path == "registration.py"
    evidence = result.evidence[0]
    resolved = restarted.evidence.resolve(
        "rag_app", "r1", evidence.source_snapshot_ref, evidence.evidence_id
    )
    assert resolved["excerpt"] == PROFILE
    assert evidence.retrieval_method == "semantic" and evidence.rank == 1
    with transaction(harness.engine) as store:
        assert store.session.scalar(select(func.count()).select_from(CodeIndexEntry)) == 2
    assert set(inspect(harness.engine).get_table_names()) == tables_before
    assert "rag_vectors_v1" not in tables_before


def test_stack_line_beats_semantics_and_top_k(harness: Harness) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    result = harness.service.retrieve(
        query(stack_trace='File "C:\\permitted\\payment.py", line 2, in payment', top_k=1)
    )
    assert len(result.evidence) == 1 and result.evidence[0].file_path == "payment.py"
    assert result.evidence[0].exact_tier == 2 and result.evidence[0].retrieval_method == "hybrid"


def test_stack_symbol_priority_without_fabricated_line(harness: Harness) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    result = harness.service.retrieve(query(stack_trace='File "payment.py", line 999, in payment'))
    assert result.evidence[0].file_path == "payment.py" and result.evidence[0].exact_tier == 1
    assert result.evidence[0].end_line == 2


@pytest.mark.parametrize("change", ["modify", "delete", "add"])
def test_same_revision_mutation_rejected_old_evidence_preserved(
    harness: Harness, change: str
) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    if change == "modify":
        (harness.root / "registration.py").write_text("profile = 2\n", encoding="utf-8")
    elif change == "delete":
        (harness.root / "registration.py").unlink()
    else:
        (harness.root / "new.py").write_text("profile = 3\n", encoding="utf-8")
    with pytest.raises(RevisionConflict, match="new revision"):
        harness.service.index("rag_app", "r1")
    assert harness.service.retrieve(query()).evidence[0].excerpt == PROFILE


def test_new_revision_handles_changed_deleted_and_cached_content(harness: Harness) -> None:
    write_sources(harness)
    (harness.root / "unchanged.py").write_text("def email():\n    return 1\n", encoding="utf-8")
    harness.service.index("rag_app", "r1")
    old = harness.service.retrieve(query()).evidence[0]
    harness.register("r2")
    (harness.root / "registration.py").write_text(
        PROFILE.replace('["name"]', '.get("name")'), encoding="utf-8"
    )
    (harness.root / "payment.py").unlink()
    report = harness.service.index("rag_app", "r2")
    assert report.files == 2 and report.embedded == 1 and report.cached == 1
    current = harness.service.retrieve(query("r2"))
    assert all(
        item.repository_revision == "r2" and item.file_path != "payment.py"
        for item in current.evidence
    )
    assert current.evidence[0].evidence_id != old.evidence_id
    assert harness.service.retrieve(query()).evidence[0] == old


def test_duplicate_content_embedded_once_but_distinct_citations(harness: Harness) -> None:
    (harness.root / "one.py").write_text(PROFILE, encoding="utf-8")
    (harness.root / "two.py").write_text(PROFILE, encoding="utf-8")
    report = harness.service.index("rag_app", "r1")
    result = harness.service.retrieve(query())
    assert report.embedded == 1 and report.chunks == 2
    assert len({item.evidence_id for item in result.evidence}) == 2
    assert len({item.content_hash for item in result.evidence}) == 1


def test_empty_unavailable_and_missing_revision(harness: Harness) -> None:
    assert harness.service.retrieve(query()).status == "unavailable"
    report = harness.service.index("rag_app", "r1")
    result = harness.service.retrieve(query())
    assert report.chunks == 0 and result.status == "empty" and result.evidence == []
    missing = harness.service.retrieve(query("unknown"))
    assert missing.status == "unavailable" and missing.reason == "REVISION_UNAVAILABLE"


def test_cross_application_isolation(harness: Harness) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    harness.register("r1", "other_app", "other")
    (harness.settings.demo_root / "other" / "other.py").write_text(PROFILE, encoding="utf-8")
    harness.service.index("other_app", "r1")
    other = harness.service.retrieve(query(application_id="other_app"))
    assert other.evidence and all(
        item.application_id == "other_app" and item.file_path == "other.py"
        for item in other.evidence
    )
    item = other.evidence[0]
    with pytest.raises(IndexUnavailable, match="scope"):
        harness.service.evidence.resolve(
            "rag_app", "r1", item.source_snapshot_ref, item.evidence_id
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"search_query": ""},
        {"top_k": 0},
        {"top_k": 21},
        {"repository_revision": "../main"},
        {"application_id": "../id"},
        {"run_id": "run"},
    ],
)
def test_invalid_queries(changes: dict) -> None:
    with pytest.raises(ValidationError):
        query(**changes)


def test_missing_trace_file_has_no_invented_citations(harness: Harness) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    harness.encoder.fail = True
    result = harness.service.retrieve(query(stack_trace='File "missing.py", line 2, in invented'))
    assert result.evidence == [] and result.status == "unavailable" and not result.semantic_used
    exact = harness.service.retrieve(
        query(stack_trace='File "registration.py", line 2, in registration')
    )
    assert exact.status == "partial" and exact.evidence[0].retrieval_method == "stack_line"


def test_corrupt_artifact_excluded(harness: Harness) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    evidence = harness.service.retrieve(query()).evidence[0]
    with transaction(harness.engine) as store:
        artifact = store.records(Artifact).get(evidence.artifact_id)
    (harness.settings.artifact_root / artifact.storage_key).write_bytes(b"tampered")
    result = harness.service.retrieve(query(stack_trace='File "registration.py", line 2'))
    assert result.reason == "CITATIONS_UNAVAILABLE"
    assert not any(item.evidence_id == evidence.evidence_id for item in result.evidence)


def test_corrupt_vector_is_honest_exact_only(harness: Harness) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    with harness.service.cache.session() as session:
        vector = session.scalar(select(Vector))
        assert vector is not None
        vector.data = b"broken"
    result = harness.service.retrieve(query(stack_trace='File "registration.py", line 2'))
    assert result.status == "partial" and not result.semantic_used
    assert result.evidence[0].retrieval_method == "stack_line"


def test_index_rollback_and_retry(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    write_sources(harness)
    original = harness.service.evidence._artifact
    calls = 0

    def fail(*args: Any, **kwargs: Any) -> str:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("synthetic disk failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(harness.service.evidence, "_artifact", fail)
    with pytest.raises(OSError):
        harness.service.index("rag_app", "r1")
    with transaction(harness.engine) as store:
        assert store.session.scalar(select(func.count()).select_from(CodeIndexEntry)) == 0
        assert store.session.scalar(select(func.count()).select_from(Artifact)) == 1
    assert harness.service.retrieve(query()).evidence == []
    monkeypatch.setattr(harness.service.evidence, "_artifact", original)
    assert harness.service.index("rag_app", "r1").chunks == 2


def test_foreign_cache_database_is_never_changed(harness: Harness) -> None:
    harness.rag.index_root.mkdir()
    import sqlite3

    path = harness.rag.index_root / "vectors-v1.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES ('preserve')")
    before = path.read_bytes()
    with pytest.raises(IndexUnavailable, match="incompatible"):
        harness.service.index("rag_app", "r1")
    assert path.read_bytes() == before


def test_source_permission_and_storage_overlap(harness: Harness) -> None:
    harness.settings.permitted_workspaces.clear()
    with pytest.raises(SourceRejected, match="not permitted"):
        harness.service.index("rag_app", "r1")
    harness.register("r2")
    harness.rag.index_root = harness.root / "index"
    with pytest.raises(SourceRejected, match="separate"):
        harness.service.index("rag_app", "r2")


def test_ambiguous_suffix_and_traversal_stack_paths() -> None:
    assert matching_path("/root/src/a.py", {"a.py", "src/a.py"}) is None
    assert matching_path("a.py", {"src/a.py", "other/a.py"}) is None
    assert hints('File "../secret.py", line 1\nFile "https://x/a.py", line 2') == []
    assert hints("at run (C:\\work\\src\\app.ts:42:7)")[0].line == 42


def test_cached_collection_metadata_is_not_source_text(harness: Harness) -> None:
    write_sources(harness)
    harness.service.index("rag_app", "r1")
    with harness.service.cache.session() as session:
        collection = session.scalar(select(Collection))
        assert collection is not None
        assert "return profile" not in json.dumps(collection.members)
    with harness.engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
