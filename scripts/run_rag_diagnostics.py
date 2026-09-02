#!/usr/bin/env python3
"""Comprehensive diagnostic runner for the Shikshak AI RAG Module.

Executes all unit, integration, and eval test cases across multiple documents.
"""

import sys
import os
import time

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.rag.src.models import ParsedDocument, Chunk, DetectedStructure
from modules.rag.src.service import RAGService
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.grounding.extractor import parse_grounded_citations
from modules.rag.src.chunking.chunker import count_tokens, split_text_into_token_chunks
from tests.fixtures.sample_docs import (
    get_physics_notes_markdown,
    get_hindi_biology_markdown,
    get_single_paragraph_doc,
    get_unstructured_wall_of_text,
    create_sample_docx_bytes,
    create_sample_pptx_bytes
)

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_case(name: str, func):
    """Execute a single test case with timing and status output."""
    t0 = time.time()
    print(f"  {BLUE}►{RESET} Running: {name:<55}", end="", flush=True)
    try:
        func()
        dt = (time.time() - t0) * 1000
        print(f"[{GREEN}PASS{RESET}] ({dt:.1f}ms)")
        return True
    except Exception as e:
        dt = (time.time() - t0) * 1000
        print(f"[{RED}FAIL{RESET}] ({dt:.1f}ms) -> {e}")
        return False


def main():
    print(f"\n{BOLD}======================================================================{RESET}")
    print(f"{BOLD}Shikshak AI — RAG Module Comprehensive Diagnostics{RESET}")
    print(f"{BOLD}======================================================================{RESET}\n")

    service = RAGService(vector_store=ChromaVectorStoreAdapter(persist_dir=":memory:"))
    passed = 0
    total = 0

    # ------------------------------------------------------------------------
    print(f"{BOLD}[1] Contract Schema Conformity (§4 & §14){RESET}")
    # ------------------------------------------------------------------------
    def test_contract_schema():
        doc = ParsedDocument(
            document_id="test_id",
            source_lang="en",
            chunks=[
                Chunk(
                    chunk_id="chunk_001",
                    text="Sample chunk",
                    section_title="Intro",
                    page_or_slide=1,
                    embedding_ref="ref#1"
                )
            ],
            detected_structure=DetectedStructure(chapters=["Intro"], key_terms=["sample"])
        )
        d = doc.model_dump()
        assert "document_id" in d and "source_lang" in d and "chunks" in d and "detected_structure" in d
        assert d["chunks"][0]["chunk_id"] == "chunk_001"
        assert d["detected_structure"]["chapters"] == ["Intro"]

    total += 1
    if run_case("Contract.md §4 ParsedDocument Schema", test_contract_schema):
        passed += 1

    # ------------------------------------------------------------------------
    print(f"\n{BOLD}[2] Multi-Format Ingestion & Structure Parsing{RESET}")
    # ------------------------------------------------------------------------
    def test_markdown_ingest():
        doc = service.ingest_document(
            file_bytes=get_physics_notes_markdown().encode("utf-8"),
            filename="physics.md"
        )
        assert len(doc.chunks) >= 3
        assert doc.source_lang == "en"
        assert len(doc.detected_structure.chapters) >= 3

    def test_hindi_ingest():
        doc = service.ingest_document(
            file_bytes=get_hindi_biology_markdown().encode("utf-8"),
            filename="biology_hi.md"
        )
        assert doc.source_lang == "hi"
        assert len(doc.chunks) >= 2

    def test_docx_ingest():
        doc = service.ingest_document(
            file_bytes=create_sample_docx_bytes(),
            filename="quantum.docx"
        )
        assert len(doc.chunks) >= 1

    def test_pptx_ingest():
        doc = service.ingest_document(
            file_bytes=create_sample_pptx_bytes(),
            filename="thermo.pptx"
        )
        assert len(doc.chunks) >= 1
        assert doc.chunks[0].page_or_slide is not None

    for name, fn in [
        ("Markdown Hierarchy & Equation Ingestion", test_markdown_ingest),
        ("Hindi (Devanagari) Language Detection & Ingestion", test_hindi_ingest),
        ("DOCX Document & Table Parsing", test_docx_ingest),
        ("PPTX Presentation & Slide Number Extraction", test_pptx_ingest),
    ]:
        total += 1
        if run_case(name, fn):
            passed += 1

    # ------------------------------------------------------------------------
    print(f"\n{BOLD}[3] Edge Cases (§5.1 & §7){RESET}")
    # ------------------------------------------------------------------------
    def test_single_paragraph():
        doc = service.ingest_document(
            file_bytes=get_single_paragraph_doc().encode("utf-8"),
            filename="short.txt"
        )
        assert len(doc.chunks) == 1

    def test_unstructured_wall_of_text():
        doc = service.ingest_document(
            file_bytes=get_unstructured_wall_of_text().encode("utf-8"),
            filename="wall.txt"
        )
        assert len(doc.chunks) >= 1
        assert doc.detected_structure.chapters == []

    def test_min_chunk_merge_guard():
        sentences = [f"This is sentence {i} on electromagnetic radiation." for i in range(40)]
        chunks = split_text_into_token_chunks(" ".join(sentences), target_tokens=300, min_chunk_tokens=50)
        for c in chunks:
            assert count_tokens(c) >= 50

    for name, fn in [
        ("Edge Case: 1-Paragraph Short Upload", test_single_paragraph),
        ("Edge Case: Unstructured Wall-of-Text", test_unstructured_wall_of_text),
        ("Edge Case: 301-Token Min-Chunk Merge Guard", test_min_chunk_merge_guard),
    ]:
        total += 1
        if run_case(name, fn):
            passed += 1

    # ------------------------------------------------------------------------
    print(f"\n{BOLD}[4] Hybrid Retrieval & Reranker Pipeline{RESET}")
    # ------------------------------------------------------------------------
    physics_doc = service.ingest_document(
        file_bytes=get_physics_notes_markdown().encode("utf-8"),
        filename="physics_main.md"
    )

    def test_hybrid_retrieval():
        res = service.retrieve_context(
            document_id=physics_doc.document_id,
            query_text="What is the equation for electrical power and Ohm's law?",
            top_k=3
        )
        assert res.has_sufficient_context is True
        assert len(res.chunks) > 0
        assert any("V = I * R" in c.text or "Power" in c.text for c in res.chunks)

    def test_insufficient_context_fallback():
        res = service.retrieve_context(
            document_id=physics_doc.document_id,
            query_text="Ancient Greek architecture parthenon columns",
            top_k=3,
            relevance_threshold=0.99
        )
        assert res.has_sufficient_context is False
        assert res.risk_level == "high_hallucination_risk"

    for name, fn in [
        ("Hybrid Retrieval (Dense + Sparse + RRF)", test_hybrid_retrieval),
        ("Zero-Match Insufficient Context Fallback", test_insufficient_context_fallback),
    ]:
        total += 1
        if run_case(name, fn):
            passed += 1

    # ------------------------------------------------------------------------
    print(f"\n{BOLD}[5] Grounding Prompt Formatting & Citation Verification{RESET}")
    # ------------------------------------------------------------------------
    def test_grounding_prompt():
        ctx = service.get_grounded_prompt(
            document_id=physics_doc.document_id,
            query_text="Electric current",
            top_k=2
        )
        assert "[chunk_" in ctx.formatted_prompt_context
        assert "grounded_on:" in ctx.formatted_prompt_context

    def test_citation_parsing_and_hallucination_detection():
        valid_pool = ["chunk_001", "chunk_002"]
        valid_resp = "Electric current is charge over time. grounded_on: [chunk_001]"
        _, cited, risk = parse_grounded_citations(valid_resp, valid_candidate_ids=valid_pool)
        assert cited == ["chunk_001"]
        assert risk is None

        # Hallucination test
        fake_resp = "Invented fact. grounded_on: [chunk_fake_999]"
        _, _, risk_fake = parse_grounded_citations(fake_resp, valid_candidate_ids=valid_pool)
        assert risk_fake is not None

    for name, fn in [
        ("Grounding Prompt Formatting with [chunk_id] tags", test_grounding_prompt),
        ("Citation Extraction & Hallucination Risk Detection", test_citation_parsing_and_hallucination_detection),
    ]:
        total += 1
        if run_case(name, fn):
            passed += 1

    # ------------------------------------------------------------------------
    print(f"\n{BOLD}======================================================================{RESET}")
    if passed == total:
        print(f"{GREEN}{BOLD}ALL {passed}/{total} DIAGNOSTIC CASES PASSED SUCCESSFULLY!{RESET}")
    else:
        print(f"{YELLOW}{BOLD}{passed}/{total} CASES PASSED ({total - passed} FAILED){RESET}")
    print(f"{BOLD}======================================================================{RESET}\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
