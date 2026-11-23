"""Syntax-aware chunks preserve actual complete source lines and stable identities."""

import pytest

from app.agents.diagnosis.code_rag.chunking import CodeChunker
from app.agents.diagnosis.code_rag.contracts import BoundSource, CodeChunk, SourceFile
from app.agents.diagnosis.code_rag.errors import SourceRejected
from app.agents.diagnosis.code_rag.hashing import digest
from tests.diagnosis.conftest import Harness


def chunks(harness: Harness, text: str, path: str = "sample.py") -> list[CodeChunk]:
    file = SourceFile(
        file_path=path,
        language="python" if path.endswith(".py") else "javascript",
        content=text,
        content_hash=digest(text.encode()),
        size_bytes=len(text.encode()),
    )
    return harness.service.chunker.chunks(harness.service.catalog.bind("rag_app", "r1"), file)


def test_python_boundaries_lines_and_stability(harness: Harness) -> None:
    text = (
        'value = 1\n\n@decorator\ndef first():\n    return "profile"\n\n'
        "class Service:\n    def run(self):\n        return 2\n"
    )
    result = chunks(harness, text)
    first = next(chunk for chunk in result if chunk.symbol == "first")
    method = next(chunk for chunk in result if chunk.symbol == "Service.run")
    assert (first.start_line, first.end_line) == (3, 5)
    assert (method.start_line, method.end_line) == (8, 9)
    for chunk in result:
        assert chunk.content == "".join(
            text.splitlines(keepends=True)[chunk.start_line - 1 : chunk.end_line]
        )
    assert result == chunks(harness, text)
    other = chunks(harness, text, "other.py")
    assert (
        first.content_hash == next(chunk for chunk in other if chunk.symbol == "first").content_hash
    )
    assert (
        first.evidence_id != next(chunk for chunk in other if chunk.symbol == "first").evidence_id
    )


def test_large_function_overlap_and_bounded_fallback(harness: Harness) -> None:
    harness.rag.max_chunk_lines = 6
    harness.rag.overlap_lines = 2
    text = "def large():\n" + "    value = 1\n" * 30
    result = chunks(harness, text)
    assert len(result) > 1
    assert all(
        chunk.symbol == "large" and chunk.end_line - chunk.start_line < 6 for chunk in result
    )
    assert result[1].start_line == result[0].end_line - 1
    assert result[-1].end_line == 31
    assert chunks(harness, "def broken(:\n  1\n")[0].strategy == "python_syntax_fallback"
    assert (
        chunks(harness, "export const value = 1;", "file.js")[0].strategy == "complete_line_windows"
    )


def test_empty_and_single_long_line(harness: Harness) -> None:
    assert chunks(harness, "\n   \n") == []
    with pytest.raises(SourceRejected, match="line exceeds"):
        chunks(harness, "x" * (harness.rag.max_chunk_chars + 1))


def test_revision_changes_chunk_identity(harness: Harness) -> None:
    text = "def same():\n    return 1\n"
    before = chunks(harness, text)[0]
    source = BoundSource("rag_app", "r2", "ref", harness.root)
    file = SourceFile(
        file_path="sample.py",
        language="python",
        content=text,
        content_hash=digest(text.encode()),
        size_bytes=len(text),
    )
    after = CodeChunker(harness.rag).chunks(source, file)[0]
    assert before.content_hash == after.content_hash and before.evidence_id != after.evidence_id
