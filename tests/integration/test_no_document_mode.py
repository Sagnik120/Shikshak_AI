"""Comprehensive Boundary & Real-World Scenario Test Suite for Topic-Only Teaching Mode.

Covers:
1. Boundary Cases:
   - None, empty string, and whitespace-only document_id ("   ", "\\t\\n")
   - Non-existent document ID querying an empty or populated vector store
   - Empty and special character query strings
   - Extreme top_k (1, 50) and relevance_threshold (0.0, 0.99) values
2. Real-World Hackathon Scenarios:
   - PS Spec §4 verbatim query: "Teach me React for a technical interview"
   - PS Spec §4 verbatim query: "Teach me Artificial Intelligence from the beginning"
   - Multilingual query in Hindi: "मुझे न्यूटन के गति के नियम समझाइए"
   - Dynamic Transition: Topic-only start -> Document upload mid-session -> Grounded retrieval
   - JSON Serialization & WebSocket payload compatibility
"""

import json
import pytest
from modules.rag.src.service import RAGService
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from tests.fixtures.sample_docs import get_physics_notes_markdown


class TestNoDocumentBoundaryAndScenarios:
    """Deep boundary and real-world scenario verification for topic-only teaching."""

    @pytest.fixture
    def rag_service(self):
        # Isolated in-memory Chroma instance for pristine test execution
        vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
        return RAGService(vector_store=vector_store)

    # =========================================================================
    # 1. BOUNDARY VALUE TESTS
    # =========================================================================

    @pytest.mark.parametrize("doc_id", [None, "", "   ", "\t\n  \r\n"])
    def test_all_falsy_and_whitespace_document_ids_trigger_topic_only(self, rag_service, doc_id):
        """All variations of empty/whitespace document_id must trigger topic-only mode safely."""
        result = rag_service.retrieve_context(
            document_id=doc_id,
            query_text="Explain Dijkstra's algorithm"
        )
        assert result.document_id is None
        assert result.has_sufficient_context is False
        assert result.risk_level == "no_document_context"
        assert result.chunks == []
        assert result.candidate_chunks == []

    @pytest.mark.parametrize("query", ["", "   ", "??? !@#$%^&*()", "a" * 1000])
    def test_boundary_query_texts_without_document(self, rag_service, query):
        """Empty, special-character, or extremely long query strings must not cause exceptions."""
        result = rag_service.retrieve_context(
            document_id=None,
            query_text=query
        )
        assert result.document_id is None
        assert result.has_sufficient_context is False
        assert result.risk_level == "no_document_context"

        ctx = rag_service.get_grounded_prompt(document_id=None, query_text=query)
        assert ctx.has_sufficient_context is False
        assert ctx.risk_flag == "no_document_context"
        assert "no source document was provided" in ctx.formatted_prompt_context.lower()

    @pytest.mark.parametrize("top_k,threshold", [
        (1, 0.0),
        (50, 0.99),
        (10, 0.50),
    ])
    def test_extreme_retrieval_parameters_without_document(self, rag_service, top_k, threshold):
        """Extreme top_k and threshold bounds must be cleanly accepted in topic-only mode."""
        result = rag_service.retrieve_context(
            document_id=None,
            query_text="Explain binary search trees",
            top_k=top_k,
            relevance_threshold=threshold
        )
        assert result.has_sufficient_context is False
        assert result.risk_level == "no_document_context"
        assert result.chunks == []

    def test_nonexistent_document_id_returns_high_hallucination_risk(self, rag_service):
        """Non-empty document ID that does not exist in store should flag high_hallucination_risk.

        Distinguishes between 'no document provided' (topic-only) and 'document missing/unindexed'
        (data retrieval failure).
        """
        result = rag_service.retrieve_context(
            document_id="doc_missing_uuid_9999",
            query_text="Explain quantum entanglement"
        )
        assert result.document_id == "doc_missing_uuid_9999"
        assert result.has_sufficient_context is False
        assert result.risk_level == "high_hallucination_risk"
        assert result.chunks == []

        ctx = rag_service.get_grounded_prompt(
            document_id="doc_missing_uuid_9999",
            query_text="Explain quantum entanglement"
        )
        assert ctx.has_sufficient_context is False
        assert ctx.risk_flag == "low_context_fallback_to_general_knowledge"
        assert "no high-confidence document excerpts found" in ctx.formatted_prompt_context.lower()

    # =========================================================================
    # 2. REAL-WORLD SPEC SCENARIOS
    # =========================================================================

    def test_real_world_spec_query_react_interview(self, rag_service):
        """Spec §4 verbatim: 'Teach me React for a technical interview' (no upload)."""
        ctx = rag_service.get_grounded_prompt(
            document_id=None,
            query_text="Teach me React for a technical interview"
        )
        assert ctx.has_sufficient_context is False
        assert ctx.risk_flag == "no_document_context"
        assert ctx.candidate_chunk_ids == []

        prompt = ctx.formatted_prompt_context
        assert "topic-based teaching mode" in prompt
        assert "do not fabricate citations" in prompt.lower()
        assert "grounded_on: []" in prompt

    def test_real_world_spec_query_ai_from_beginning(self, rag_service):
        """Spec §4 verbatim: 'Teach me Artificial Intelligence from the beginning' (no upload)."""
        ctx = rag_service.get_grounded_prompt(
            document_id=None,
            query_text="Teach me Artificial Intelligence from the beginning"
        )
        assert ctx.has_sufficient_context is False
        assert ctx.risk_flag == "no_document_context"
        assert "grounded_on: []" in ctx.formatted_prompt_context

    def test_real_world_hindi_multilingual_topic_query(self, rag_service):
        """Spec §8 requirement: Hindi topic query without document."""
        hindi_query = "मुझे न्यूटन के गति के नियम समझाइए"
        result = rag_service.retrieve_context(document_id=None, query_text=hindi_query)
        assert result.document_id is None
        assert result.has_sufficient_context is False
        assert result.risk_level == "no_document_context"

        ctx = rag_service.get_grounded_prompt(document_id=None, query_text=hindi_query)
        assert ctx.risk_flag == "no_document_context"
        assert ctx.candidate_chunk_ids == []

    def test_real_world_session_transition_topic_to_uploaded_doc(self, rag_service):
        """Scenario: Student begins in topic-only mode, then uploads a document mid-session.

        Verifies that RAGService transitions cleanly from topic-only mode to full
        grounded retrieval with real chunks and citations for the same service instance.
        """
        # Step 1: Student asks a general topic question before uploading
        step1_res = rag_service.retrieve_context(
            document_id=None,
            query_text="What is Ohm's law?"
        )
        assert step1_res.risk_level == "no_document_context"
        assert step1_res.chunks == []

        step1_ctx = rag_service.get_grounded_prompt(
            document_id=None,
            query_text="What is Ohm's law?"
        )
        assert step1_ctx.candidate_chunk_ids == []
        assert "grounded_on: []" in step1_ctx.formatted_prompt_context

        # Step 2: Student uploads their physics textbook
        md_bytes = get_physics_notes_markdown().encode("utf-8")
        parsed_doc = rag_service.ingest_document(
            file_bytes=md_bytes,
            filename="physics_notes.md",
            mime_type="text/markdown"
        )
        assert parsed_doc.document_id is not None
        assert len(parsed_doc.chunks) >= 3

        # Step 3: Student asks the same question with the newly uploaded document_id
        step3_res = rag_service.retrieve_context(
            document_id=parsed_doc.document_id,
            query_text="What is Ohm's law?",
            top_k=3
        )
        # Now it MUST be grounded with real chunks!
        assert step3_res.has_sufficient_context is True
        assert step3_res.risk_level == "low"
        assert len(step3_res.chunks) > 0
        assert any("ohm" in c.text.lower() for c in step3_res.chunks)

        step3_ctx = rag_service.get_grounded_prompt(
            document_id=parsed_doc.document_id,
            query_text="What is Ohm's law?",
            top_k=3
        )
        assert step3_ctx.has_sufficient_context is True
        assert len(step3_ctx.candidate_chunk_ids) > 0
        assert "source material:" not in step3_ctx.formatted_prompt_context.lower() or "you are teaching using only" in step3_ctx.formatted_prompt_context.lower()

    # =========================================================================
    # 3. JSON SERIALIZATION & WEBSOCKET PROTOCOL COMPATIBILITY
    # =========================================================================

    def test_pydantic_json_roundtrip_compatibility(self, rag_service):
        """Ensures topic-only models cleanly serialize to JSON for FastAPI and WebSocket transport."""
        result = rag_service.retrieve_context(
            document_id=None,
            query_text="Explain quicksort vs mergesort"
        )
        data = result.model_dump()
        assert data["document_id"] is None
        assert data["has_sufficient_context"] is False
        assert data["risk_level"] == "no_document_context"
        assert data["chunks"] == []

        # JSON roundtrip
        json_str = result.model_dump_json()
        deserialized = json.loads(json_str)
        assert deserialized["risk_level"] == "no_document_context"

        ctx = rag_service.get_grounded_prompt(
            document_id=None,
            query_text="Explain quicksort vs mergesort"
        )
        ctx_data = ctx.model_dump()
        assert ctx_data["has_sufficient_context"] is False
        assert ctx_data["risk_flag"] == "no_document_context"
        assert ctx_data["candidate_chunk_ids"] == []
