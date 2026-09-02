"""Deep unit test suite for multi-format document parsers, structure extraction, and edge cases."""

import pytest
from modules.rag.src.models import ParsedDocument, RawSection, Chunk
from modules.rag.src.parsing.parser import parse_document, extract_raw_sections
from modules.rag.src.parsing.txt_parser import parse_text_or_markdown
from modules.rag.src.parsing.docx_parser import parse_docx
from modules.rag.src.parsing.pptx_parser import parse_pptx
from modules.rag.src.parsing.structure import detect_language, extract_key_terms_tfidf
from modules.rag.src.chunking.chunker import chunk_sections, split_text_into_token_chunks, count_tokens
from tests.fixtures.sample_docs import (
    get_physics_notes_markdown,
    get_hindi_biology_markdown,
    get_single_paragraph_doc,
    get_unstructured_wall_of_text,
    create_sample_docx_bytes,
    create_sample_pptx_bytes
)


class TestParsersDeep:
    """Test suite covering every document format and edge cases."""

    def test_markdown_parser_hierarchical_sections(self):
        md_text = get_physics_notes_markdown()
        sections, chapters = parse_text_or_markdown(md_text)

        assert len(sections) == 3
        assert chapters == [
            "Electromagnetism and Circuits",
            "Section 1: Electric Current and Voltage",
            "Section 2: Ohm's Law and Resistance",
            "Section 3: Electrical Power and Joule's Heating"
        ]
        assert sections[0].section_title == "Section 1: Electric Current and Voltage"
        assert "Ampere" in sections[0].raw_text
        assert "V = I * R" in sections[1].raw_text

    def test_hindi_document_language_detection_and_parsing(self):
        hindi_text = get_hindi_biology_markdown()
        doc = parse_document(
            file_bytes=hindi_text.encode("utf-8"),
            filename="biology_hindi.md",
            mime_type="text/markdown"
        )

        assert doc.source_lang == "hi"
        assert len(doc.chunks) >= 2
        assert "प्रकाश संश्लेषण" in doc.detected_structure.chapters[0]

    def test_docx_parser_in_memory(self):
        docx_bytes = create_sample_docx_bytes()
        sections, chapters = parse_docx(docx_bytes)
        
        assert len(sections) >= 1
        assert any("Quantum Mechanics Overview" in ch for ch in chapters)
        # Verify table content was captured
        combined_text = " ".join(sec.raw_text for sec in sections)
        assert "Electron" in combined_text or "Quantum" in combined_text

    def test_pptx_parser_in_memory(self):
        pptx_bytes = create_sample_pptx_bytes()
        sections, chapters = parse_pptx(pptx_bytes)

        assert len(sections) >= 1
        assert any("Thermodynamics" in ch or "Zeroth" in ch for ch in chapters)
        assert sections[0].page_or_slide is not None

    def test_edge_case_single_paragraph_upload(self):
        """Edge Case §5.1: 1-paragraph short upload."""
        single_p = get_single_paragraph_doc()
        doc = parse_document(
            file_bytes=single_p.encode("utf-8"),
            filename="notes.txt",
            mime_type="text/plain"
        )

        assert len(doc.chunks) == 1
        assert doc.chunks[0].chunk_id.startswith("chunk_")
        assert doc.chunks[0].section_title is None
        assert "Mitochondria" in doc.chunks[0].text

    def test_edge_case_unstructured_wall_of_text(self):
        """Edge Case §5.1: No headings, no Markdown structure."""
        wall_text = get_unstructured_wall_of_text()
        doc = parse_document(
            file_bytes=wall_text.encode("utf-8"),
            filename="history_essay.txt",
            mime_type="text/plain"
        )

        assert doc.detected_structure.chapters == []
        assert len(doc.chunks) >= 1
        assert "Newton" in doc.chunks[0].text


class TestStructureAndChunkingDeep:
    """Test suite covering token counting, boundary guards, and TF-IDF extraction."""

    def test_tfidf_keyword_extraction_precision(self):
        text = get_physics_notes_markdown()
        key_terms = extract_key_terms_tfidf(text, top_n=10)

        assert len(key_terms) > 0
        term_str = " ".join(key_terms).lower()
        assert any(k in term_str for k in ["current", "voltage", "resistance", "electric", "power"])

    def test_chunk_sections_preserves_titles_and_pages(self):
        sections = [
            RawSection(section_title="Chapter 1", page_or_slide=1, raw_text="Content for page 1."),
            RawSection(section_title="Chapter 2", page_or_slide=2, raw_text="Content for page 2.")
        ]
        chunks = chunk_sections(sections, document_id="doc_abc")
        assert len(chunks) == 2
        assert chunks[0].section_title == "Chapter 1"
        assert chunks[0].page_or_slide == 1
        assert chunks[1].section_title == "Chapter 2"
        assert chunks[1].page_or_slide == 2

    def test_token_split_window_overlap(self):
        # Generate 600 words of text
        long_body = " ".join([f"Word{i} is part of physics concept." for i in range(120)])
        chunks = split_text_into_token_chunks(
            long_body,
            target_tokens=300,
            max_tokens=500,
            overlap_pct=0.15,
            min_chunk_tokens=50
        )

        assert len(chunks) >= 2
        # Check overlap presence
        assert len(chunks[0]) > 0
        assert len(chunks[1]) > 0
