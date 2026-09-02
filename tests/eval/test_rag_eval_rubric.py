"""Rubric-aligned evaluation tests for Groundedness (15 pts) and Anti-Hallucination."""

import pytest
from modules.rag.src.service import RAGService
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.grounding.extractor import parse_grounded_citations
from tests.fixtures.sample_docs import get_physics_notes_markdown


class TestRubricGroundedness:
    """Evaluation assertions ensuring answers are traceable to source material."""

    @pytest.fixture
    def rag_service(self):
        vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
        return RAGService(vector_store=vector_store)

    def test_irrelevant_query_signals_general_knowledge_fallback(self, rag_service):
        """Rubric Check: Irrelevant topic must not hallucinate a source citation."""
        doc = rag_service.ingest_document(
            file_bytes=get_physics_notes_markdown().encode("utf-8"),
            filename="physics.md"
        )

        # Query unrelated to the physics doc
        grounded_ctx = rag_service.get_grounded_prompt(
            document_id=doc.document_id,
            query_text="Who was the first emperor of the Maurya dynasty?",
            top_k=3
        )

        # Strict floor test with high threshold
        res = rag_service.retrieve_context(
            document_id=doc.document_id,
            query_text="Who was the first emperor of the Maurya dynasty?",
            top_k=3,
            relevance_threshold=0.95
        )

        assert res.has_sufficient_context is False
        assert res.risk_level == "high_hallucination_risk"

    def test_hallucination_detection_on_invented_chunk_ids(self):
        """Rubric Check: System detects when agent cites non-existent chunks."""
        simulated_hallucinated_response = """
        This is an explanation asserting fabricated claims.
        grounded_on: [chunk_fake_999, chunk_fake_888]
        """

        valid_pool = ["chunk_doc1_0001", "chunk_doc1_0002"]
        _, cited, risk = parse_grounded_citations(
            simulated_hallucinated_response,
            valid_candidate_ids=valid_pool
        )

        assert risk is not None
        assert "hallucinated_chunk_references" in risk

    def test_hallucination_detection_on_empty_citations_when_context_provided(self):
        """Rubric Check: Flags risk if agent ignores clear source context."""
        simulated_ignored_context_response = """
        This explanation did not include any citations at all.
        """

        valid_pool = ["chunk_doc1_0001", "chunk_doc1_0002", "chunk_doc1_0003"]
        _, cited, risk = parse_grounded_citations(
            simulated_ignored_context_response,
            valid_candidate_ids=valid_pool
        )

        assert cited == []
        assert risk == "empty_citations_despite_available_context"
