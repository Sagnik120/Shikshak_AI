"""Unit tests for structure-aware semantic chunker."""

from modules.rag.src.models import RawSection
from modules.rag.src.chunking.chunker import (
    chunk_sections,
    split_text_into_token_chunks,
    count_tokens
)


def test_chunking_preserves_section_boundaries():
    """Verify chunker never merges text across distinct section boundaries."""
    sec1 = RawSection(
        section_title="Section A",
        page_or_slide=1,
        raw_text="This is text from Section A talking about concept 1."
    )
    sec2 = RawSection(
        section_title="Section B",
        page_or_slide=2,
        raw_text="This is text from Section B talking about concept 2."
    )

    chunks = chunk_sections([sec1, sec2], document_id="test_doc")
    assert len(chunks) == 2
    assert chunks[0].section_title == "Section A"
    assert chunks[0].page_or_slide == 1
    assert "Section A" in chunks[0].text

    assert chunks[1].section_title == "Section B"
    assert chunks[1].page_or_slide == 2
    assert "Section B" in chunks[1].text


def test_min_chunk_merge_guard_on_301_tokens():
    """Verify 301-token test per detailed_design.md §7:

    Boundary logic does not create an orphan trailing chunk (min-chunk-size guard merges small trailing chunk).
    """
    # Create text with sentences totaling roughly 310 words
    sentences = [f"This is sentence number {i} explaining physics in detail." for i in range(40)]
    long_text = " ".join(sentences)

    chunks = split_text_into_token_chunks(
        long_text,
        target_tokens=300,
        max_tokens=500,
        min_chunk_tokens=50
    )

    # All resulting chunks must be substantive; no 1-token orphan chunk
    for c in chunks:
        assert count_tokens(c) >= 50


def test_short_section_single_chunk():
    """Section shorter than target tokens remains a single chunk without extra overlap padding."""
    short_section = RawSection(
        section_title="Slide 1",
        page_or_slide=1,
        raw_text="Brief bullet point 1.\nBrief bullet point 2."
    )
    chunks = chunk_sections([short_section], document_id="test_doc")
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk_test_doc_0001"
