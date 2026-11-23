"""Python syntax boundaries and complete-line overlapping windows for other source."""

import ast
from dataclasses import dataclass

from app.agents.diagnosis.code_rag.config import RagSettings
from app.agents.diagnosis.code_rag.contracts import BoundSource, CodeChunk, SourceFile
from app.agents.diagnosis.code_rag.errors import SourceRejected
from app.agents.diagnosis.code_rag.hashing import digest, identity


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    symbol: str


def definition_start(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> int:
    return min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])


def python_spans(text: str, line_count: int) -> list[Span]:
    """Partition module/class gaps and top-level definitions without executing code."""
    tree = ast.parse(text)
    spans: list[Span] = []

    def partition(nodes: list[ast.stmt], start: int, end: int, parent: str) -> None:
        cursor = start
        for node in nodes:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            first, last = definition_start(node), node.end_lineno or node.lineno
            if first > cursor:
                spans.append(Span(cursor, first - 1, parent or "<module>"))
            symbol = f"{parent}.{node.name}" if parent else node.name
            if isinstance(node, ast.ClassDef):
                partition(node.body, first, last, symbol)
            else:
                spans.append(Span(first, last, symbol))
            cursor = last + 1
        if cursor <= end:
            spans.append(Span(cursor, end, parent or "<module>"))

    partition(tree.body, 1, line_count, "")
    return spans


class CodeChunker:
    """Preserve complete source lines, decorators, symbols and bounded function context."""

    def __init__(self, settings: RagSettings) -> None:
        self.settings = settings

    def chunks(self, source: BoundSource, file: SourceFile) -> list[CodeChunk]:
        lines = file.content.splitlines(keepends=True)
        if not file.content.strip():
            return []
        strategy = "complete_line_windows"
        spans = [Span(1, len(lines), "")]
        if file.language == "python":
            try:
                spans = python_spans(file.content, len(lines))
                strategy = "python_ast"
            except (SyntaxError, ValueError, RecursionError):
                strategy = "python_syntax_fallback"
        result: list[CodeChunk] = []
        for span in spans:
            start = span.start
            while start <= span.end:
                end, size = start - 1, 0
                while end < span.end and end - start + 1 < self.settings.max_chunk_lines:
                    length = len(lines[end])
                    if size + length > self.settings.max_chunk_chars:
                        break
                    size += length
                    end += 1
                if end < start:
                    raise SourceRejected(
                        "SOURCE_LINE_LIMIT", "A source line exceeds the chunk limit."
                    )
                content = "".join(lines[start - 1 : end])
                if content.strip():
                    content_hash = digest(content.encode())
                    result.append(
                        CodeChunk(
                            evidence_id=identity(
                                "chunk",
                                source.application_id,
                                source.repository_revision,
                                file.file_path,
                                start,
                                end,
                                content_hash,
                            ),
                            application_id=source.application_id,
                            repository_revision=source.repository_revision,
                            file_path=file.file_path,
                            symbol=span.symbol,
                            start_line=start,
                            end_line=end,
                            content=content,
                            content_hash=content_hash,
                            language=file.language,
                            strategy=strategy,
                        )
                    )
                if end == span.end:
                    break
                start = max(start + 1, end - self.settings.overlap_lines + 1)
        return result
