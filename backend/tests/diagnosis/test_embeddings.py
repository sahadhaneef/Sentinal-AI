"""Provider validation never turns failures into fabricated semantic matches."""

import math
from pathlib import Path

import pytest

from app.agents.diagnosis.code_rag.embeddings import LocalSemanticProvider, validate_vectors
from app.agents.diagnosis.code_rag.errors import EmbeddingUnavailable, InvalidEmbedding
from tests.diagnosis.conftest import Harness, TestEncoder


@pytest.mark.parametrize(
    "vectors,count,dimensions",
    [
        ([], 1, 2),
        ([[1]], 1, 2),
        ([[1, math.nan]], 1, 2),
        ([[1, math.inf]], 1, 2),
        ([[0, 0]], 1, 2),
        ([[True, 1]], 1, 2),
        ([["1", 2]], 1, 2),
        ([[1, 2]], 1, 0),
    ],
)
def test_invalid_vectors(vectors: list, count: int, dimensions: int) -> None:
    with pytest.raises(InvalidEmbedding):
        validate_vectors(vectors, count, dimensions)


def test_normalized_and_deterministic_test_encoder() -> None:
    encoder = TestEncoder()
    assert encoder.documents(["profile"]) == encoder.documents(["profile"])
    assert validate_vectors([[3, 4]], 1, 2) == [[0.6, 0.8]]


def test_local_provider_missing_weights_has_no_fallback(tmp_path: Path) -> None:
    with pytest.raises(EmbeddingUnavailable, match="pinned local"):
        LocalSemanticProvider(tmp_path).query("registration error")


def test_failed_index_provider_leaves_no_published_collection(harness: Harness) -> None:
    (harness.root / "app.py").write_text("profile = 1", encoding="utf-8")
    harness.encoder.fail = True
    with pytest.raises(EmbeddingUnavailable, match="failed safely"):
        harness.service.index("rag_app", "r1")
    from app.agents.diagnosis.code_rag.contracts import RetrievalRequest

    result = harness.service.retrieve(
        RetrievalRequest(application_id="rag_app", repository_revision="r1", search_query="profile")
    )
    assert result.status == "unavailable" and result.evidence == []
