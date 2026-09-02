"""Evaluation and integration tests for hybrid retrieval, RRF, and threshold fallbacks."""

from modules.rag.src.models import Chunk
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.retrieval.rrf import reciprocal_rank_fusion
from modules.rag.src.retrieval.retriever import HybridRetriever


def test_reciprocal_rank_fusion_scoring():
    """Verify RRF formula correctly scores items appearing in multiple candidate lists."""
    dense_list = [
        {"chunk_id": "chunk_1", "text": "Text 1", "score": 0.95},
        {"chunk_id": "chunk_2", "text": "Text 2", "score": 0.85}
    ]
    sparse_list = [
        {"chunk_id": "chunk_2", "text": "Text 2", "score": 5.0},
        {"chunk_id": "chunk_3", "text": "Text 3", "score": 4.0}
    ]

    fused = reciprocal_rank_fusion([dense_list, sparse_list], k=60, top_n=3)
    assert len(fused) == 3

    # chunk_2 appears in both lists (rank 2 in dense + rank 1 in sparse)
    # score(chunk_2) = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ≈ 0.0161 + 0.01639 ≈ 0.0325
    # score(chunk_1) = 1/61 ≈ 0.01639
    assert fused[0]["chunk_id"] == "chunk_2"
    assert fused[0]["score"] > fused[1]["score"]


def test_retrieval_insufficient_context_relevance_floor():
    """Edge Case §5.1 / §7: Query with no relevant content triggers high hallucination risk flag."""
    vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
    
    # Store physics chunks
    chunks = [
        Chunk(
            chunk_id="chunk_elec_001",
            text="Electric current is the flow of electric charge through a conductor.",
            section_title="Current",
            page_or_slide=1
        )
    ]
    vector_store.upsert(
        document_id="doc_physics",
        chunks=chunks,
        dense_embeddings=[[0.1] * 128],
        sparse_weights=[{"current": 1.0, "charge": 1.0}]
    )

    retriever = HybridRetriever(vector_store=vector_store)

    # Search for an unrelated query with low threshold override to test detection
    result = retriever.retrieve(
        document_id="doc_physics",
        query_text="medieval history castles knights",
        top_k=5,
        relevance_threshold=0.99  # Strict floor
    )

    # Must flag low context rather than fabricating high confidence
    assert result.document_id == "doc_physics"
    assert result.has_sufficient_context is False
    assert result.risk_level == "high_hallucination_risk"
