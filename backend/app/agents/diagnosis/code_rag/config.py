"""Optional Diagnosis configuration, independent of protected core settings."""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import BACKEND_ROOT

LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
}
CHUNKER_VERSION = "python-ast-complete-lines-v1"
FILTER_VERSION = "source-allowlist-secret-scan-v1"


class RagSettings(BaseSettings):
    """Runtime environment variables only; no new keys enter the shared dotenv file."""

    model_config = SettingsConfigDict(env_prefix="SENTINEL_RAG_", env_file=None, extra="forbid")
    index_root: Path = BACKEND_ROOT / "artifacts" / "code-rag-index"
    model_root: Path = BACKEND_ROOT.parent / ".tools" / "code-rag-models" / "bge-small-en-v1.5"
    allowed_extensions: frozenset[str] = frozenset(LANGUAGES)
    max_file_bytes: int = Field(default=131072, ge=1, le=1048576)
    max_total_bytes: int = Field(default=2097152, ge=1, le=16777216)
    max_files: int = Field(default=256, ge=1, le=2000)
    max_entries: int = Field(default=4096, ge=1, le=20000)
    max_depth: int = Field(default=24, ge=1, le=64)
    max_chunks: int = Field(default=2000, ge=1, le=10000)
    max_chunk_lines: int = Field(default=48, ge=4, le=200)
    max_chunk_chars: int = Field(default=1600, ge=128, le=4096)
    overlap_lines: int = Field(default=4, ge=0, le=32)
    embedding_batch_size: int = Field(default=16, ge=1, le=64)
    embedding_threads: int = Field(default=2, ge=1, le=8)
    min_semantic_score: float = Field(default=0.25, ge=-1, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_policy(self) -> "RagSettings":
        if not self.allowed_extensions or not self.allowed_extensions <= LANGUAGES.keys():
            raise ValueError("Choose only supported source-code extensions")
        if self.overlap_lines >= self.max_chunk_lines:
            raise ValueError("Chunk overlap must be smaller than the line window")
        if self.max_file_bytes > self.max_total_bytes:
            raise ValueError("The file limit cannot exceed the total ingestion limit")
        for root in (self.index_root, self.model_root):
            if not root.is_absolute():
                raise ValueError("Configure absolute cache/model roots")
        return self
