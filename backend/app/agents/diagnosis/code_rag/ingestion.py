"""Read permitted source as untrusted data, never as commands or Python imports."""

import os
import stat
from collections import Counter
from pathlib import Path

from app.agents.diagnosis.code_rag.config import LANGUAGES, RagSettings
from app.agents.diagnosis.code_rag.contracts import BoundSource, IngestionReport, SourceFile
from app.agents.diagnosis.code_rag.errors import SourceRejected
from app.agents.diagnosis.code_rag.hashing import digest
from app.core.logging import redact
from app.db.types import validate_relative_key

EXCLUDED_DIRECTORIES = frozenset(
    {
        "node_modules",
        "venv",
        "__pycache__",
        "dist",
        "build",
        "target",
        "vendor",
        "artifacts",
        "generated",
        "coverage",
        "site-packages",
        "third_party",
        "secrets",
        "credentials",
        "certs",
        "keys",
        "out",
        "bin",
        "obj",
    }
)
SENSITIVE_NAMES = ("secret", "credential", "password", "private_key", "id_rsa", "id_ed25519")


def reject_redirects(path: Path) -> None:
    """Reject symlinks and Windows junctions in a path or any existing ancestor."""
    for component in [*reversed(path.absolute().parents), path.absolute()]:
        if component.is_symlink() or component.is_junction():
            raise SourceRejected(
                "UNSAFE_PATH", "Redirected source/storage paths are not permitted."
            )


class SourceIngestion:
    """Bounded no-follow scanning; callers obtain the bound root from the source catalog."""

    def __init__(self, settings: RagSettings) -> None:
        self.settings = settings

    def read_file(self, source: BoundSource, relative: str) -> SourceFile:
        """Read a complete UTF-8 source file after checking confinement and file identity."""
        try:
            validate_relative_key(relative)
            parts = relative.lower().split("/")
            if any(part.startswith(".") or part in EXCLUDED_DIRECTORIES for part in parts):
                raise SourceRejected("EXCLUDED_PATH", "This source path is excluded.")
            name = parts[-1]
            if any(term in name for term in SENSITIVE_NAMES) or name in {
                "config.py",
                "settings.py",
            }:
                raise SourceRejected("EXCLUDED_PATH", "This source path is excluded.")
            if (
                Path(relative).suffix.lower() not in self.settings.allowed_extensions
                or ".generated." in name
                or ".min." in name
            ):
                raise SourceRejected("UNSUPPORTED_SOURCE", "This file type is not permitted.")
            reject_redirects(source.root)
            path = source.root / relative
            reject_redirects(path)
            path.resolve(strict=True).relative_to(source.root.resolve(strict=True))
            before = path.stat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise SourceRejected(
                    "UNSAFE_FILE", "Only ordinary unlinked source files are accepted."
                )
            if before.st_size > self.settings.max_file_bytes:
                raise SourceRejected("FILE_LIMIT", "A source file exceeds the configured limit.")
            with path.open("rb") as stream:
                opened = os.fstat(stream.fileno())
                data = stream.read(self.settings.max_file_bytes + 1)
            after = path.stat()
            reject_redirects(path)
            if (before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns) != (
                after.st_ino,
                after.st_dev,
                after.st_size,
                after.st_mtime_ns,
            ) or (opened.st_ino, opened.st_dev) != (before.st_ino, before.st_dev):
                raise SourceRejected(
                    "SOURCE_CHANGED", "Source changed while being captured; retry safely."
                )
            if len(data) > self.settings.max_file_bytes:
                raise SourceRejected("FILE_LIMIT", "A source file exceeds the configured limit.")
            text = data.decode("utf-8")
            if "\x00" in text:
                raise SourceRejected("ENCODING", "Binary source is not supported.")
            if redact(text) != text or "-----BEGIN " in text:
                raise SourceRejected(
                    "SENSITIVE_CONTENT", "Potential credentials must not be indexed."
                )
            return SourceFile(
                file_path=relative,
                language=LANGUAGES[path.suffix.lower()],
                content=text,
                content_hash=digest(data),
                size_bytes=len(data),
            )
        except UnicodeDecodeError:
            raise SourceRejected("ENCODING", "Source must be UTF-8 text.") from None
        except (OSError, ValueError):
            raise SourceRejected(
                "SOURCE_UNREADABLE", "A source file cannot be read safely."
            ) from None

    def scan(self, source: BoundSource) -> IngestionReport:
        """Exclude disallowed material and fail closed on unreadable/inconsistent input."""
        reject_redirects(source.root)
        if not source.root.is_dir():
            raise SourceRejected("ROOT_UNAVAILABLE", "The configured source root is unavailable.")
        files: list[SourceFile] = []
        skipped: Counter[str] = Counter()
        total = 0
        pending = [source.root]
        visited = 0
        while pending:
            folder = pending.pop()
            try:
                entries = []
                for entry in folder.iterdir():
                    visited += 1
                    if visited > self.settings.max_entries:
                        raise SourceRejected(
                            "INGESTION_LIMIT", "The repository exceeds scan limits."
                        )
                    entries.append(entry)
                entries.sort(key=lambda path: path.name)
            except OSError:
                raise SourceRejected(
                    "SOURCE_UNREADABLE", "A source directory is unreadable."
                ) from None
            for path in entries:
                name = path.name.lower()
                if path.is_symlink() or path.is_junction():
                    skipped["link"] += 1
                    continue
                if name.startswith(".") or name in EXCLUDED_DIRECTORIES:
                    skipped["excluded"] += 1
                    continue
                if any(term in name for term in SENSITIVE_NAMES) or name in {
                    "config.py",
                    "settings.py",
                }:
                    skipped["sensitive_name"] += 1
                    continue
                if path.is_dir():
                    if len(path.relative_to(source.root).parts) > self.settings.max_depth:
                        raise SourceRejected(
                            "INGESTION_LIMIT", "The repository exceeds depth limits."
                        )
                    pending.append(path)
                    continue
                if (
                    path.suffix.lower() not in self.settings.allowed_extensions
                    or ".generated." in name
                    or ".min." in name
                ):
                    skipped["unsupported"] += 1
                    continue
                relative = path.relative_to(source.root).as_posix()
                try:
                    file = self.read_file(source, relative)
                except SourceRejected as error:
                    if error.code not in {
                        "ENCODING",
                        "SENSITIVE_CONTENT",
                        "FILE_LIMIT",
                        "UNSAFE_FILE",
                    }:
                        raise
                    skipped[error.code.lower()] += 1
                    continue
                total += file.size_bytes
                files.append(file)
                if len(files) > self.settings.max_files or total > self.settings.max_total_bytes:
                    raise SourceRejected(
                        "INGESTION_LIMIT", "The repository exceeds ingestion limits."
                    )
        return IngestionReport(
            files=sorted(files, key=lambda file: file.file_path),
            skipped=dict(skipped),
            total_bytes=total,
        )
