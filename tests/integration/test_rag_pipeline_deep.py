"""Integration test suite covering the full RAG pipeline across multiple documents and queries."""

import pytest
from modules.rag.src.service import RAGService
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.grounding.extractor import parse_grounded_citations
from tests.fixtures.sample_docs import (
    get_physics_notes_markdown,
    get_hindi_biology_markdown,
    create_sample_docx_bytes,
    create_sample_pptx_bytes
)


class TestRAGPipelineIntegration:
    """Integration test suite for RAG Ingestion -> Embedding -> Retrieval -> Grounding."""

    @pytest.fixture
    def rag_service(self):
        # Use in-memory Chroma for isolated integration tests
        vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
        return RAGService(vector_store=vector_store)

    def test_full_markdown_pipeline(self, rag_service):
        md_bytes = get_physics_notes_markdown().encode("utf-8")
        
        # 1. Ingest
        doc = rag_service.ingest_document(
            file_bytes=md_bytes,
            filename="physics.md",
            mime_type="text/markdown"
        )
        assert len(doc.chunks) >= 3
        assert all(c.embedding_ref != "" for c in doc.chunks)

        # 2. Query 1: Ohm's Law
        res1 = rag_service.retrieve_context(
            document_id=doc.document_id,
            query_text="What is Ohm's law and the formula for resistance?",
            top_k=3
        )
        assert res1.has_sufficient_context is True
        assert len(res1.chunks) > 0
        top_text = res1.chunks[0].text
        assert "Ohm" in top_text or "V = I * R" in top_text or "proportional" in top_text

        # 3. Query 2: Joule's heating
        res2 = rag_service.retrieve_context(
            document_id=doc.document_id,
            query_text="Explain Joule's heating law",
            top_k=3
        )
        assert len(res2.chunks) > 0
        assert any("Joule" in c.text or "H = I^2" in c.text for c in res2.chunks)

    def test_multilingual_hindi_pipeline(self, rag_service):
        hindi_bytes = get_hindi_biology_markdown().encode("utf-8")

        # 1. Ingest
        doc = rag_service.ingest_document(
            file_bytes=hindi_bytes,
            filename="photosynthesis_hi.md",
            mime_type="text/markdown"
        )
        assert doc.source_lang == "hi"

        # 2. Query in Hindi
        res = rag_service.retrieve_context(
            document_id=doc.document_id,
            query_text="प्रकाश संश्लेषण की रासायनिक अभिक्रिया क्या है?",
            top_k=2
        )
        assert len(res.chunks) > 0
        assert any("6CO2" in c.text or "ग्लूकोज" in c.text or "प्रकाश संश्लेषण" in c.text for c in res.chunks)

    def test_grounding_prompt_and_citation_roundtrip(self, rag_service):
        md_bytes = get_physics_notes_markdown().encode("utf-8")
        doc = rag_service.ingest_document(
            file_bytes=md_bytes,
            filename="physics.md"
        )

        prompt_ctx = rag_service.get_grounded_prompt(
            document_id=doc.document_id,
            query_text="Electric current definition",
            top_k=2
        )

        assert prompt_ctx.has_sufficient_context is True
        candidate_ids = prompt_ctx.candidate_chunk_ids
        assert len(candidate_ids) > 0

        # Simulate Explainer Agent response citing the first chunk
        simulated_llm_response = f"""
        Electric current is the rate of flow of electric charge through a conductor.
        It is measured in Amperes.

        grounded_on: [{candidate_ids[0]}]
        """

        clean_text, cited_ids, risk = parse_grounded_citations(
            simulated_llm_response,
            valid_candidate_ids=candidate_ids
        )

        assert cited_ids == [candidate_ids[0]]
        assert "grounded_on:" not in clean_text
        assert risk is None
