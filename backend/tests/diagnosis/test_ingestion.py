"""Source filtering, bounded reads and filesystem trust boundaries."""

import os
import subprocess
from pathlib import Path
from typing import IO, Any

import pytest

from app.agents.diagnosis.code_rag.errors import SourceRejected
from app.agents.diagnosis.code_rag.ingestion import SourceIngestion
from tests.diagnosis.conftest import Harness


def test_filters_and_valid_source(harness: Harness) -> None:
    files = {
        "valid.py": "def hello():\n    return 1\n",
        "component.ts": "export const hello = 1;\n",
        ".env": "PASSWORD=hidden",
        "config.py": "value = 2",
        "secret.py": "value = 3",
        "notes.txt": "ignored",
        "node_modules/lib.js": "ignored",
        ".git/internal.py": "ignored",
        "generated/auto.py": "ignored",
        "dist/bundle.js": "ignored",
        "credentials.py": "ignored",
        "binary.py": "\x00",
        "unsafe.py": 'api_key = "example"',
        "bad.py": "invalid encoding placeholder",
    }
    for name, content in files.items():
        path = harness.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (harness.root / "bad.py").write_bytes(b"\xff\xfe")
    report = harness.service.ingestion.scan(harness.service.catalog.bind("rag_app", "r1"))
    assert [file.file_path for file in report.files] == ["component.ts", "valid.py"]
    assert report.skipped["sensitive_content"] == 1
    assert report.skipped["encoding"] == 2


@pytest.mark.parametrize(
    "relative",
    [
        "../outside.py",
        "/outside.py",
        "C:/outside.py",
        ".env",
        "secret.py",
        "file.txt",
        "node_modules/lib.py",
    ],
)
def test_rejects_direct_disallowed_reads(harness: Harness, relative: str) -> None:
    source = harness.service.catalog.bind("rag_app", "r1")
    with pytest.raises(SourceRejected):
        harness.service.ingestion.read_file(source, relative)


def test_limits(harness: Harness) -> None:
    (harness.root / "large.py").write_bytes(b"x" * 200)
    harness.rag.max_file_bytes = 100
    report = harness.service.ingestion.scan(harness.service.catalog.bind("rag_app", "r1"))
    assert report.files == [] and report.skipped["file_limit"] == 1
    harness.rag.max_file_bytes = 300
    harness.rag.max_total_bytes = 100
    with pytest.raises(SourceRejected, match="ingestion limits"):
        harness.service.index("rag_app", "r1")


def test_unreadable_file(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    path = harness.root / "valid.py"
    path.write_text("x = 1", encoding="utf-8")
    original = Path.open

    def deny(self: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if self == path:
            raise PermissionError("private absolute path")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny)
    with pytest.raises(SourceRejected, match="cannot be read safely"):
        harness.service.index("rag_app", "r1")


def test_link_escape_and_redirected_root(harness: Harness, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "escape.py").write_text("never_embed = 1", encoding="utf-8")
    link = harness.root / "escape"
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True
        )
    else:
        link.symlink_to(outside, target_is_directory=True)
    report = harness.service.ingestion.scan(harness.service.catalog.bind("rag_app", "r1"))
    assert report.files == [] and report.skipped["link"] == 1
    source = harness.service.catalog.bind("rag_app", "r1")
    with pytest.raises(SourceRejected, match="Redirected"):
        harness.service.ingestion.read_file(source, "escape/escape.py")


def test_hardlinks_are_not_ingested(harness: Harness) -> None:
    original = harness.root / "first.py"
    original.write_text("value = 1", encoding="utf-8")
    os.link(original, harness.root / "second.py")
    report = harness.service.ingestion.scan(harness.service.catalog.bind("rag_app", "r1"))
    assert report.files == [] and report.skipped["unsafe_file"] == 2


def test_scan_entry_and_depth_limits(harness: Harness) -> None:
    for index in range(4):
        (harness.root / f"{index}.txt").touch()
    ingestion = SourceIngestion(harness.rag.model_copy(update={"max_entries": 2}))
    with pytest.raises(SourceRejected, match="scan limits"):
        ingestion.scan(harness.service.catalog.bind("rag_app", "r1"))
    nested = harness.root / "a" / "b"
    nested.mkdir(parents=True)
    ingestion = SourceIngestion(harness.rag.model_copy(update={"max_depth": 1}))
    with pytest.raises(SourceRejected, match="depth limits"):
        ingestion.scan(harness.service.catalog.bind("rag_app", "r1"))
