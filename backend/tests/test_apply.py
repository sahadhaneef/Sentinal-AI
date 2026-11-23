"""Tests for controlled patch application, hash verification, path traversal protection, and rollback."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import CandidateStaleError, ForbiddenError
from app.db.models import Application, Incident, IncidentRun, PatchCandidate, ValidationResult
from app.services.apply import PatchApplicationService, apply_unified_diff, compute_patch_hash

def test_apply_unified_diff_unit():
    original = (
        "def hello():\n"
        "    # comment\n"
        "    msg = 'bad'\n"
        "    return msg\n"
    )
    diff = (
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -1,4 +1,4 @@\n"
        " def hello():\n"
        "     # comment\n"
        "-    msg = 'bad'\n"
        "+    msg = 'good'\n"
        "     return msg\n"
    )
    patched = apply_unified_diff(original, diff)
    assert "msg = 'good'" in patched
    assert "msg = 'bad'" not in patched


def test_patch_hash_computation():
    diff = "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-a\n+b\n"
    hash1 = compute_patch_hash(diff)
    # Windows CRLF should produce same hash after normalization
    hash2 = compute_patch_hash(diff.replace("\n", "\r\n"))
    assert hash1.startswith("sha256:")
    assert hash1 == hash2


@pytest.mark.asyncio
async def test_strict_hash_mismatch_rejected(db_session: AsyncSession):
    original = (
        "def hello():\n"
        "    # comment\n"
        "    msg = 'bad'\n"
        "    return msg\n"
    )
    diff = (
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -1,4 +1,4 @@\n"
        " def hello():\n"
        "     # comment\n"
        "-    msg = 'bad'\n"
        "+    msg = 'good'\n"
        "     return msg\n"
    )
    patched = apply_unified_diff(original, diff)
    assert "msg = 'good'" in patched
    assert "msg = 'bad'" not in patched


def test_patch_hash_computation():
    diff = "--- a/test.py\n+++ b/test.py\n@@ -1 +1 @@\n-a\n+b\n"
    hash1 = compute_patch_hash(diff)
    # Windows CRLF should produce same hash after normalization
    hash2 = compute_patch_hash(diff.replace("\n", "\r\n"))
    assert hash1.startswith("sha256:")
    assert hash1 == hash2


async def test_strict_hash_mismatch_rejected(db_session: AsyncSession):
    service = PatchApplicationService(db_session)
    diff = "--- a/src/registration.py\n+++ b/src/registration.py\n@@ -1 +1 @@\n-a\n+b\n"
    wrong_hash = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    with pytest.raises(CandidateStaleError):
        service._verify_hash_strict(diff, wrong_hash)


async def test_path_traversal_blocked(db_session: AsyncSession):
    service = PatchApplicationService(db_session)
    traversal_paths = [
        "../outside.py",
        "../../etc/passwd",
        "/etc/shadow",
        "subdir/../../escape.py",
    ]
    for p in traversal_paths:
        with pytest.raises(ForbiddenError):
            service._assert_safe_path(p)


async def test_non_allowlisted_app_blocked(db_session: AsyncSession):
    service = PatchApplicationService(db_session)
    with pytest.raises(ForbiddenError):
        service._assert_allowed_app("unauthorized_production_app")


async def test_successful_patch_application_and_verification(db_session: AsyncSession, tmp_path: Path):
    """Real end-to-end patch application modifying target file and passing verification."""
    # Setup isolated test workspace
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    src_dir = workspace / "src"
    src_dir.mkdir()
    tests_dir = workspace / "tests"
    tests_dir.mkdir()

    # Original buggy file
    orig_code = (
        "def register_user(payload: dict) -> dict:\n"
        '    """Register a user. BUG: does not guard against missing profile."""\n'
        "    # BUG: This line will raise KeyError/AttributeError when profile is None\n"
        '    name = payload["profile"]["name"]\n'
        "    return create_user(name)\n"
        "\n"
        "def create_user(name: str) -> dict:\n"
        '    return {"status": "created", "name": name}\n'
        "\n"
        "def registration_handler(request_body: dict) -> dict:\n"
        "    try:\n"
        "        return register_user(request_body)\n"
        "    except (KeyError, TypeError, AttributeError) as e:\n"
        '        return {"error": f"Registration failed: {e}"}\n'
    )
    (src_dir / "registration.py").write_text(orig_code, encoding="utf-8")

    # Test file that verifies recovery
    test_code = (
        "import sys, os\n"
        "sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n"
        "from src.registration import registration_handler\n"
        "res = registration_handler({'profile': None})\n"
        "assert 'error' not in res, f'Failed with error: {res}'\n"
        "assert res.get('status') == 'created'\n"
        "print('PASS')\n"
    )
    (tests_dir / "test_registration.py").write_text(test_code, encoding="utf-8")

    # Patch that fixes the bug
    diff = (
        "--- a/src/registration.py\n"
        "+++ b/src/registration.py\n"
        "@@ -1,7 +1,8 @@\n"
        " def register_user(payload: dict) -> dict:\n"
        '     """Register a user. BUG: does not guard against missing profile."""\n'
        "     # BUG: This line will raise KeyError/AttributeError when profile is None\n"
        '-    name = payload["profile"]["name"]\n'
        '+    profile = payload.get("profile") or {}\n'
        '+    name = profile.get("name", "Guest")\n'
        "     return create_user(name)\n"
    )
    patch_hash = compute_patch_hash(diff)

    service = PatchApplicationService(db_session)
    service.settings.demo_workspace_path = str(workspace)

    incident = Incident(
        id="inc_test_apply",
        application_id="app_demo",
        source_event_id="evt_01",
        fingerprint="fp_apply_test",
        error_type="NullReferenceError",
        message="Test apply",
        repository_revision="abc123",
    )
    run = IncidentRun(id="run_test_apply", incident_id="inc_test_apply")
    candidate = PatchCandidate(
        id="patch_test_apply",
        incident_id="inc_test_apply",
        run_id="run_test_apply",
        version=1,
        base_revision="abc123",
        patch_hash=patch_hash,
        diff_content=diff,
        changed_files_json=json.dumps(["src/registration.py"]),
        status="approved",
    )

    db_session.add(incident)
    db_session.add(run)
    db_session.add(candidate)
    await db_session.commit()

    result = await service.apply(incident, run, candidate)

    assert result["status"] == "resolved"
    assert result["restore_status"] == "not_needed"
    # Check that file was actually modified
    modified_text = (src_dir / "registration.py").read_text(encoding="utf-8")
    assert 'profile = payload.get("profile") or {}' in modified_text
    assert 'name = payload["profile"]["name"]' not in modified_text


async def test_failed_verification_triggers_rollback(db_session: AsyncSession, tmp_path: Path):
    """If verification fails, snapshot must be restored completely."""
    workspace = tmp_path / "workspace_fail"
    workspace.mkdir()
    src_dir = workspace / "src"
    src_dir.mkdir()
    tests_dir = workspace / "tests"
    tests_dir.mkdir()

    orig_content = "# original content that should be restored\ndef untouched(): pass\n"
    (src_dir / "registration.py").write_text(orig_content, encoding="utf-8")

    # Test file that intentionally fails
    test_code = (
        "import sys\n"
        "print('Assertion failure simulation', file=sys.stderr)\n"
        "sys.exit(1)\n"
    )
    (tests_dir / "test_registration.py").write_text(test_code, encoding="utf-8")

    diff = (
        "--- a/src/registration.py\n"
        "+++ b/src/registration.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-# original content that should be restored\n"
        "+# modified content that causes test failure\n"
        " def untouched(): pass\n"
    )
    patch_hash = compute_patch_hash(diff)

    service = PatchApplicationService(db_session)
    service.settings.demo_workspace_path = str(workspace)

    incident = Incident(
        id="inc_test_fail",
        application_id="app_demo",
        source_event_id="evt_02",
        fingerprint="fp_fail_test",
        error_type="NullReferenceError",
        message="Test fail",
        repository_revision="abc123",
    )
    run = IncidentRun(id="run_test_fail", incident_id="inc_test_fail")
    candidate = PatchCandidate(
        id="patch_test_fail",
        incident_id="inc_test_fail",
        run_id="run_test_fail",
        version=1,
        base_revision="abc123",
        patch_hash=patch_hash,
        diff_content=diff,
        changed_files_json=json.dumps(["src/registration.py"]),
        status="approved",
    )

    db_session.add(incident)
    db_session.add(run)
    db_session.add(candidate)
    await db_session.commit()

    result = await service.apply(incident, run, candidate)

    assert result["status"] == "unresolved"
    assert result["restore_status"] == "restored"
    # Ensure workspace file content was rolled back to original!
    restored_text = (src_dir / "registration.py").read_text(encoding="utf-8")
    assert restored_text == orig_content
