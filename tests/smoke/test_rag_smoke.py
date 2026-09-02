"""Fast smoke test to verify RAG module imports, contract conformity, and basic flow."""

import pytest
from modules.rag.src.models import ParsedDocument, Chunk, DetectedStructure
from modules.rag.src.parsing.parser import parse_document
from modules.rag.src.service import RAGService
from tests.fixtures.sample_docs import get_physics_notes_markdown


def test_rag_smoke_imports():
    """Verify all critical classes and helpers import without error."""
    from modules.rag.src import (
        ParsedDocument,
        Chunk,
        DetectedStructure,
        parse_document,
        chunk_sections,
        get_embedding_adapter,
        ChromaVectorStoreAdapter,
        HybridRetriever,
        format_grounding_context_block,
        parse_grounded_citations,
        RAGService
    )
    assert ParsedDocument is not None
    assert RAGService is not None


def test_rag_smoke_e2e_flow():
    """Verify parse -> embed -> index -> retrieve -> prompt format smoke pipeline."""
    sample_md = get_physics_notes_markdown()
    service = RAGService()

    # 1. Ingest
    parsed_doc = service.ingest_document(
        file_bytes=sample_md.encode("utf-8"),
        filename="physics_test.md",
        mime_type="text/markdown"
    )

    assert isinstance(parsed_doc, ParsedDocument)
    assert len(parsed_doc.chunks) >= 3
    assert parsed_doc.source_lang == "en"
    assert "Section 1: Electric Current and Voltage" in parsed_doc.detected_structure.chapters

    # 2. Retrieve
    result = service.retrieve_context(
        document_id=parsed_doc.document_id,
        query_text="What is Ohm's law formula?",
        top_k=3
    )

    assert result.document_id == parsed_doc.document_id
    assert len(result.chunks) > 0
    assert result.has_sufficient_context is True

    # 3. Grounded Prompt
    grounded_ctx = service.get_grounded_prompt(
        document_id=parsed_doc.document_id,
        query_text="What is Ohm's law formula?",
        top_k=3
    )

    assert "[chunk_" in grounded_ctx.formatted_prompt_context
    assert len(grounded_ctx.candidate_chunk_ids) > 0
    assert grounded_ctx.has_sufficient_context is True
