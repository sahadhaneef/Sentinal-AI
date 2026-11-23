import hashlib
import json

from app.core.config import BACKEND_ROOT


def test_frozen_frontend_sources_have_not_drifted_without_a_contract_decision():
    manifest = json.loads((BACKEND_ROOT / "fixtures/frontend-contract-lock.json").read_text())
    assert manifest["schema_version"] == "1.0"
    for relative, digest in manifest["files"].items():
        text = (BACKEND_ROOT.parent / relative).read_text(encoding="utf-8")
        assert hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest() == digest, relative
