"""A deploy where the embedding model cannot load must not fake grounding.

The adapters fall back to deterministic hash vectors when the model is missing.
Similarity over those is meaningless, but the numbers still look like scores, so
without a guard the classroom would cite a learner's document for content it
never matched.
"""
from unittest.mock import patch

from modules.rag.src.embedding.bge_m3 import BGEM3EmbeddingAdapter
from modules.rag.src.embedding.e5_bm25 import E5BM25EmbeddingAdapter
from modules.rag.src.models import RetrievalResult, RetrievedChunk
from modules.rag.src.service import RAGService


def _service(adapter) -> RAGService:
    service = RAGService.__new__(RAGService)  # no models loaded
    service.embedding_adapter = adapter
    service._degraded_warning_logged = False
    return service


class _Healthy:
    is_degraded = False


class _Degraded:
    is_degraded = True


def _grounded_result() -> RetrievalResult:
    return RetrievalResult(
        document_id="doc-1",
        query_text="Newton's First Law",
        chunks=[RetrievedChunk(chunk_id="c1", text="unrelated passage", score=0.99)],
        has_sufficient_context=True,
        risk_level="low",
    )


def test_a_healthy_adapter_leaves_the_result_untouched():
    result = _service(_Healthy())._guard_degraded_embeddings(_grounded_result())

    assert result.has_sufficient_context
    assert result.risk_level == "low"
    assert len(result.chunks) == 1


def test_degraded_embeddings_can_never_be_reported_as_grounded():
    result = _service(_Degraded())._guard_degraded_embeddings(_grounded_result())

    assert not result.has_sufficient_context
    assert result.risk_level == "high_hallucination_risk"
    # No chunks means no citation can be built from meaningless vectors.
    assert result.chunks == []


def test_the_degradation_warning_is_logged_once_not_per_query(caplog):
    service = _service(_Degraded())
    with caplog.at_level("ERROR"):
        for _ in range(5):
            service._guard_degraded_embeddings(_grounded_result())

    assert sum("hash fallback" in m for m in caplog.messages) == 1


def test_a_service_without_an_adapter_attribute_is_tolerated():
    """Benchmark stubs construct the service without the usual attributes."""
    service = RAGService.__new__(RAGService)
    service._degraded_warning_logged = False
    assert service._guard_degraded_embeddings(_grounded_result()).has_sufficient_context


def test_adapters_report_healthy_before_any_load_attempt():
    assert BGEM3EmbeddingAdapter().is_degraded is False
    assert E5BM25EmbeddingAdapter().is_degraded is False


def test_adapters_report_degraded_after_falling_back_to_hash_vectors():
    """The real trigger: the model libraries are unavailable at runtime."""
    adapter = BGEM3EmbeddingAdapter()
    with patch.dict("sys.modules", {"FlagEmbedding": None, "sentence_transformers": None}):
        adapter.embed_passages(["Newton's First Law states that an object at rest…"])

    assert adapter.is_degraded is True
