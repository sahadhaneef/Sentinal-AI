"""Validated local semantic embeddings; there is deliberately no test fallback."""

from __future__ import annotations

import hashlib
import math
import numbers
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from .errors import EmbeddingUnavailable, InvalidEmbedding

if TYPE_CHECKING:
    from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_REPOSITORY = "Qdrant/bge-small-en-v1.5-onnx-Q"
MODEL_REVISION = "aa8f8b060edb00e03bfdd08813a2949946c8ba55"
MODEL_FILES = {
    "config.json": "0d7726d0cdccb62ee17c03bd1595cff07199b8f8",
    "model_optimized.onnx": "51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431",
    "ort_config.json": "ca62fa095648efcf2709136afcd942d98744eb3f",
    "special_tokens_map.json": "9bbecc17cabbcbd3112c14d6982b51403b264bfa",
    "tokenizer.json": "688882a79f44442ddc1f60d70334a7ff5df0fb47",
    "tokenizer_config.json": "75305659f7795d4549f0e23688b52fa20a32f925",
    "vocab.txt": "fb140275c155a9c7c5a3b3e0e77a9e839594a938",
}


class EmbeddingProvider(Protocol):
    """Profile identifies weights, dimensions and all preprocessing behavior."""

    profile: str
    dimensions: int

    def documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...

    def query(self, text: str) -> Sequence[float]: ...


def validate_vectors(
    vectors: Sequence[Sequence[float]], count: int, dimensions: int
) -> list[list[float]]:
    """Validate cardinality and finite, nonzero vectors, then L2 normalize."""
    if dimensions < 1 or dimensions > 4096 or len(vectors) != count:
        raise InvalidEmbedding("INVALID_EMBEDDING", "Embedding cardinality is invalid.")
    result = []
    for vector in vectors:
        if len(vector) != dimensions or any(
            isinstance(value, bool) or not isinstance(value, numbers.Real) for value in vector
        ):
            raise InvalidEmbedding(
                "INVALID_EMBEDDING", "Embedding dimensions or values are invalid."
            )
        values = [float(value) for value in vector]
        norm = math.hypot(*values)
        if not all(math.isfinite(value) for value in values) or not math.isfinite(norm) or not norm:
            raise InvalidEmbedding(
                "INVALID_EMBEDDING", "Embedding values must be finite and nonzero."
            )
        result.append([value / norm for value in values])
    return result


def verify_model(root: Path) -> None:
    """Verify pinned weights and tokenizer files before loading native runtime code."""
    from .ingestion import reject_redirects

    try:
        reject_redirects(root)
        for name, expected in MODEL_FILES.items():
            path = root / name
            reject_redirects(path)
            with path.open("rb") as stream:
                data = stream.read(80 * 1024 * 1024 + 1)
            if len(data) > 80 * 1024 * 1024:
                raise ValueError("Model file exceeded size limit")
            if len(expected) == 64:
                actual = hashlib.sha256(data).hexdigest()
            else:
                actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if actual != expected:
                raise ValueError("Model checksum mismatch")
    except (OSError, ValueError):
        raise EmbeddingUnavailable(
            "MODEL_UNAVAILABLE", "Install the pinned local embedding model."
        ) from None


class LocalSemanticProvider:
    """CPU-only quantized BGE encoder, loaded lazily with network access disabled."""

    dimensions = 384
    profile = f"fastembed-0.9.1:{MODEL_REPOSITORY}@{MODEL_REVISION}:384:raw-v1"

    def __init__(self, root: Path, batch_size: int = 16, threads: int = 2) -> None:
        self.root = root
        self.batch_size = batch_size
        self.threads = threads
        self._encoder: TextEmbedding | None = None

    def _load(self) -> TextEmbedding:
        if self._encoder is None:
            verify_model(self.root)
            try:
                if version("fastembed") != "0.9.1":
                    raise ValueError("Install the pinned FastEmbed runtime")
                from fastembed import TextEmbedding

                self._encoder = TextEmbedding(
                    model_name=MODEL_NAME,
                    specific_model_path=str(self.root),
                    local_files_only=True,
                    providers=["CPUExecutionProvider"],
                    threads=self.threads,
                )
            except Exception:
                raise EmbeddingUnavailable(
                    "ENCODER_UNAVAILABLE", "Local encoder could not load."
                ) from None
        return self._encoder

    def documents(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            values = list(self._load().embed(list(texts), batch_size=self.batch_size))
            return validate_vectors(values, len(texts), self.dimensions)
        except (EmbeddingUnavailable, InvalidEmbedding):
            raise
        except Exception:
            raise EmbeddingUnavailable("ENCODER_FAILED", "Local embedding failed.") from None

    def query(self, text: str) -> list[float]:
        return self.documents([text])[0]
