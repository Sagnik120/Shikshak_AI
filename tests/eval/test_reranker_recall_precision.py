"""Deep Evaluation Test Suite: Two-Threshold Reranking, Paraphrase Recall & Out-of-Scope Precision.

Addresses Issue 1 from 01_rag_module_fix_plan_v2.md:
1. Paraphrase Recall: Verifies that natural, non-verbatim student questions
   are NOT falsely rejected by the cross-encoder and achieve has_sufficient_context=True.
2. Out-of-Scope Precision: Verifies that cross-domain queries (biology, economics, history, databases)
   are 100% rejected with has_sufficient_context=False and risk_level='high_hallucination_risk'.
3. Boundary & Extreme Cases: Whitespace, single-word queries, punctuation-only, very long queries,
   and Hinglish queries.
"""

import pytest
from modules.rag.src.service import RAGService
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from tests.fixtures.sample_docs import get_physics_notes_markdown


@pytest.fixture(scope="module")
def rag_service():
    vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
    return RAGService(vector_store=vector_store)


@pytest.fixture(scope="module")
def physics_doc(rag_service):
    md_bytes = get_physics_notes_markdown().encode("utf-8")
    doc = rag_service.ingest_document(
        file_bytes=md_bytes,
        filename="physics_circuits_eval.md",
        mime_type="text/markdown"
    )
    return doc


class TestRerankerRecallAndPrecision:
    """Comprehensive test suite for two-threshold reranking evaluation."""

    # =========================================================================
    # 1. REAL-WORLD STUDENT PARAPHRASE RECALL (In-Scope, Non-Verbatim)
    # =========================================================================

    IN_SCOPE_PARAPHRASES = [
        # (Paraphrased student question, expected keyword in target chunk)
        ("What happens to current if you increase voltage but keep resistance the same?", "directly proportional"),
        ("Why does a thicker wire carry more electric current for the same voltage?", "cross-sectional area"),
        ("If you double the length of a copper cable, how does its electrical opposition change?", "length of the conductor"),
        ("How is electrical work done related to moving electric charges?", "work done per unit charge"),
        ("What determines the rate of thermal heat generation in a circuit element?", "joule's law"),
        ("What units are used to measure the flow rate of charge in a wire?", "ampere"),
        ("Can you explain the mathematical relation between power, potential, and flow?", "p = v * i"),
        ("What is the difference between electric potential and current?", "rate of flow"),
        ("What physical conditions must stay constant for Ohm's law to hold?", "temperature"),
        ("How does resistivity influence the total resistance of an electrical wire?", "resistivity"),
    ]

    @pytest.mark.parametrize("question,expected_content", IN_SCOPE_PARAPHRASES)
    def test_paraphrased_in_scope_student_questions_retrieve_context(
        self, rag_service, physics_doc, question, expected_content
    ):
        """Student questions using conversational phrasing must retrieve context and not be rejected."""
        result = rag_service.retrieve_context(
            document_id=physics_doc.document_id,
            query_text=question,
            top_k=3
        )

        assert result.has_sufficient_context is True, (
            f"False negative! Paraphrased question was wrongly rejected: '{question}' (top score: {result.chunks[0].score if result.chunks else 0.0})"
        )
        assert result.risk_level in ("low", "moderate_relevance")
        assert len(result.chunks) > 0

        # Verify that the retrieved excerpt actually answers the question
        all_text = " ".join(c.text.lower() for c in result.chunks)
        assert expected_content.lower() in all_text, (
            f"Target chunk missing '{expected_content}'. Retrieved: {all_text[:120]}..."
        )

        # Verify grounded prompt packaging
        grounded_ctx = rag_service.get_grounded_prompt(
            document_id=physics_doc.document_id,
            query_text=question
        )
        assert grounded_ctx.has_sufficient_context is True
        assert len(grounded_ctx.candidate_chunk_ids) > 0
        assert expected_content.lower() in grounded_ctx.formatted_prompt_context.lower()

    def test_overall_paraphrase_recall_metric(self, rag_service, physics_doc):
        """Aggregate Recall evaluation: must achieve >= 90% recall across in-scope paraphrases."""
        hits = 0
        total = len(self.IN_SCOPE_PARAPHRASES)

        for question, _ in self.IN_SCOPE_PARAPHRASES:
            res = rag_service.retrieve_context(document_id=physics_doc.document_id, query_text=question)
            if res.has_sufficient_context and len(res.chunks) > 0:
                hits += 1

        recall = hits / total
        assert recall >= 0.90, f"Paraphrase recall ({recall:.1%}) dropped below 90% threshold ({hits}/{total})"

    # =========================================================================
    # 2. OUT-OF-SCOPE CROSS-DOMAIN PRECISION (Anti-Hallucination Defense)
    # =========================================================================

    OUT_OF_SCOPE_QUESTIONS = [
        "Explain the light-dependent reactions of photosynthesis in chloroplasts.",
        "How do B-Tree and LSM-tree indexes differ in relational database engines?",
        "What is the GDP of Australia in 2024 and its primary mineral exports?",
        "Describe the role of hemoglobin in oxygen transportation through human blood.",
        "Who was the first emperor of the Maurya Dynasty in ancient India?",
        "How does TCP congestion control handle packet loss using slow start?",
        "What is the chemical composition of basaltic volcanic magma?",
    ]

    @pytest.mark.parametrize("out_of_scope_query", OUT_OF_SCOPE_QUESTIONS)
    def test_out_of_scope_queries_strictly_rejected(
        self, rag_service, physics_doc, out_of_scope_query
    ):
        """Cross-domain queries must have 0% false acceptance rate and trigger high hallucination risk."""
        result = rag_service.retrieve_context(
            document_id=physics_doc.document_id,
            query_text=out_of_scope_query,
            top_k=3
        )

        assert result.has_sufficient_context is False, (
            f"False positive! Out-of-scope question was accepted: '{out_of_scope_query}'"
        )
        assert result.risk_level == "high_hallucination_risk"
        assert len(result.chunks) == 0

        # Verify prompt block forces general knowledge disclaimer and grounded_on: []
        grounded_ctx = rag_service.get_grounded_prompt(
            document_id=physics_doc.document_id,
            query_text=out_of_scope_query
        )
        assert grounded_ctx.has_sufficient_context is False
        assert grounded_ctx.candidate_chunk_ids == []
        assert "no high-confidence document excerpts found" in grounded_ctx.formatted_prompt_context.lower()
        assert "general knowledge, not from the uploaded document" in grounded_ctx.formatted_prompt_context.lower()
        assert "grounded_on: []" in grounded_ctx.formatted_prompt_context

    def test_overall_false_accept_rate_metric(self, rag_service, physics_doc):
        """Aggregate Precision evaluation: False Accept Rate for out-of-scope queries must be 0%."""
        false_accepts = 0
        total = len(self.OUT_OF_SCOPE_QUESTIONS)

        for q in self.OUT_OF_SCOPE_QUESTIONS:
            res = rag_service.retrieve_context(document_id=physics_doc.document_id, query_text=q)
            if res.has_sufficient_context:
                false_accepts += 1

        far = false_accepts / total
        assert far == 0.0, f"False accept rate ({far:.1%}) must be strictly 0% on out-of-scope queries!"

    # =========================================================================
    # 3. BOUNDARY, EXTREME & MULTILINGUAL CASES
    # =========================================================================

    @pytest.mark.parametrize("empty_query", ["", "   ", "\t\n\r", "   \n   "])
    def test_boundary_empty_and_whitespace_queries(self, rag_service, physics_doc, empty_query):
        """Empty or whitespace queries return safe high_hallucination_risk with zero chunks."""
        res = rag_service.retrieve_context(document_id=physics_doc.document_id, query_text=empty_query)
        assert res.has_sufficient_context is False
        assert res.risk_level == "high_hallucination_risk"
        assert res.chunks == []

    def test_boundary_punctuation_only_query(self, rag_service, physics_doc):
        """Punctuation-only queries do not trigger false retrieval hits."""
        res = rag_service.retrieve_context(document_id=physics_doc.document_id, query_text="??? !!! ... ---")
        assert res.has_sufficient_context is False
        assert res.risk_level == "high_hallucination_risk"

    def test_boundary_single_character_and_token_query(self, rag_service, physics_doc):
        """Single character 'V' or 'R' should query safely without crashing."""
        res = rag_service.retrieve_context(document_id=physics_doc.document_id, query_text="V")
        assert isinstance(res.has_sufficient_context, bool)
        assert isinstance(res.chunks, list)

    def test_boundary_extremely_long_query(self, rag_service, physics_doc):
        """Queries exceeding 200 words are handled gracefully without buffer overflow."""
        long_q = "Explain electric current, voltage, and resistance in circuits. " * 30
        res = rag_service.retrieve_context(document_id=physics_doc.document_id, query_text=long_q)
        assert res.has_sufficient_context is True
        assert len(res.chunks) > 0
        assert "v = i * r" in res.chunks[0].text.lower() or "current" in res.chunks[0].text.lower()

    def test_real_world_hinglish_paraphrase_query(self, rag_service, physics_doc):
        """Real-World Hinglish Demo Case: Student asks in conversational code-mixed Hindi-English."""
        hinglish_query = "Agar hum wire ka voltage badha de to current me kya change aayega?"
        res = rag_service.retrieve_context(document_id=physics_doc.document_id, query_text=hinglish_query)
        assert res.has_sufficient_context is True
        assert len(res.chunks) > 0
        # Should retrieve Ohm's law chunk
        assert any("ohm's law" in c.text.lower() or "v = i * r" in c.text.lower() for c in res.chunks)
