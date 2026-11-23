"""Explicit real-encoder smoke test using migrated, disposable synthetic databases only."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic.config import Config

from alembic import command
from app.core.config import BACKEND_ROOT, DemoWorkspace, Settings
from app.db.session import create_database_engine
from app.models import Application, Artifact, RepositoryRevision
from app.repositories.unit_of_work import transaction

from .config import RagSettings
from .contracts import RetrievalRequest
from .service import CodeRag


def verify(root: Path) -> dict[str, object]:
    """Exercise the actual local encoder, restart, exact matching and frozen citations."""
    url = f"sqlite:///{(root / 'domain.sqlite3').as_posix()}"
    previous = os.environ.get("SENTINEL_DATABASE_URL")
    try:
        os.environ["SENTINEL_DATABASE_URL"] = url
        command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
        command.check(Config(str(BACKEND_ROOT / "alembic.ini")))
    finally:
        if previous is None:
            os.environ.pop("SENTINEL_DATABASE_URL", None)
        else:
            os.environ["SENTINEL_DATABASE_URL"] = previous
    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=url,
        artifact_root=root / "content",
        demo_root=root / "source",
        permitted_workspaces={
            "sample": DemoWorkspace(
                name="Smoke sample", revision="smoke-r1", snapshot_key="smoke/snapshot"
            )
        },
    )
    rag = RagSettings(index_root=root / "index")
    source = settings.demo_root / "sample"
    source.mkdir(parents=True)
    files = {
        "registration.py": (
            "def register_user(profile):\n"
            '    """Create a new account from a signup profile."""\n'
            '    display_name = profile["name"]\n    return {"name": display_name}\n'
        ),
        "billing.py": (
            "def charge_invoice(payment, database):\n"
            '    """Charge a card for an unpaid invoice."""\n'
            "    return database.charge(payment.amount)\n"
        ),
        "storage.py": (
            "def remove_expired_files(storage):\n"
            '    """Clean old temporary files from disk."""\n'
            "    return storage.delete_expired()\n"
        ),
        ".env": "PRIVATE=excluded\n",
    }
    for name, content in files.items():
        (source / name).write_bytes(content.encode())
    engine = create_database_engine(settings)
    try:
        with transaction(engine) as store:
            store.records(Artifact).add(
                Artifact(
                    id="smoke_snapshot",
                    kind="source_snapshot",
                    storage_key="smoke/snapshot",
                    sha256="sha256:" + "a" * 64,
                    content_type="application/octet-stream",
                    size_bytes=0,
                    redacted=False,
                )
            )
            store.applications.add(
                Application(id="smoke_app", name="Smoke sample", workspace_key="sample")
            )
            revision = store.records(RepositoryRevision).add(
                RepositoryRevision(
                    application_id="smoke_app",
                    revision="smoke-r1",
                    snapshot_artifact_id="smoke_snapshot",
                )
            )
            store.applications.select_revision("smoke_app", revision.id)
        service = CodeRag(engine, settings, rag)
        first = service.index("smoke_app", "smoke-r1")
        second = service.index("smoke_app", "smoke-r1")
        request = RetrievalRequest(
            application_id="smoke_app",
            repository_revision="smoke-r1",
            search_query=(
                "A new user cannot sign up because a missing name field is accessed directly."
            ),
            top_k=3,
        )
        semantic = service.retrieve(request)
        assert semantic.semantic_used and semantic.evidence[0].file_path == "registration.py"
        exact = service.retrieve(
            request.model_copy(
                update={
                    "stack_trace": 'File "billing.py", line 3, in charge_invoice',
                    "top_k": 1,
                }
            )
        )
        assert exact.evidence[0].file_path == "billing.py" and exact.evidence[0].exact_tier == 2
        # A new service instance reads persisted vectors and reloads the actual local encoder.
        restarted = CodeRag(engine, settings, rag).retrieve(request)
        assert restarted.evidence[0].evidence_id == semantic.evidence[0].evidence_id
        assert first.embedded == 3 and second.embedded == 0 and second.cached == 3
        return {
            "first_index": first.model_dump(),
            "reindex": second.model_dump(),
            "semantic": semantic.model_dump(),
            "exact": exact.model_dump(),
            "restart_verified": True,
            "alembic_check": "passed",
        }
    finally:
        engine.dispose()


def main() -> None:
    """Print only synthetic evidence; never inspect the real local application database."""
    with TemporaryDirectory(prefix="sentinel-code-rag-smoke-") as temporary:
        result = verify(Path(temporary))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
