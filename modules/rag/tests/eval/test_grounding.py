"""Evaluation tests for grounding prompt formatting and citation verification."""

from modules.rag.src.models import RetrievedChunk
from modules.rag.src.grounding.prompt import format_grounding_context_block
from modules.rag.src.grounding.extractor import parse_grounded_citations


def test_grounding_prompt_formatting():
    """Verify grounding prompt wraps chunks with exact chunk_id tags and instructions."""
    chunks = [
        RetrievedChunk(
            chunk_id="chunk_a1b2",
            text="Ohm's law states that current is proportional to voltage: V = IR.",
            section_title="Ohm's Law",
            page_or_slide=4,
            score=0.92
        ),
        RetrievedChunk(
            chunk_id="chunk_c3d4",
            text="Resistance is measured in Ohms.",
            section_title="Ohm's Law",
            page_or_slide=5,
            score=0.85
        )
    ]

    context = format_grounding_context_block(chunks, has_sufficient_context=True)
    assert context.has_sufficient_context is True
    assert "[chunk_a1b2]" in context.formatted_prompt_context
    assert 'Section: "Ohm\'s Law"' in context.formatted_prompt_context
    assert "Page/Slide: 4" in context.formatted_prompt_context
    assert "[chunk_c3d4]" in context.formatted_prompt_context
    assert "grounded_on:" in context.formatted_prompt_context
    assert context.candidate_chunk_ids == ["chunk_a1b2", "chunk_c3d4"]


def test_parse_grounded_citations_valid():
    """Verify valid grounded_on citation extraction and prompt footer stripping."""
    llm_output = """
    Ohm's law defines the linear relationship between voltage, current, and resistance.
    Specifically, when voltage increases across a fixed resistor, current increases proportionally.
    
    grounded_on: [chunk_a1b2, chunk_c3d4]
    """
    clean_text, cited_ids, risk = parse_grounded_citations(
        llm_output,
        valid_candidate_ids=["chunk_a1b2", "chunk_c3d4"]
    )

    assert cited_ids == ["chunk_a1b2", "chunk_c3d4"]
    assert "grounded_on:" not in clean_text
    assert risk is None


def test_parse_grounded_citations_hallucination_detection():
    """Verify detection of hallucinated chunk IDs not in provided candidate context."""
    llm_output = """
    This explanation cites an imaginary chunk.
    
    grounded_on: [chunk_fake_999]
    """
    _, cited_ids, risk = parse_grounded_citations(
        llm_output,
        valid_candidate_ids=["chunk_a1b2", "chunk_c3d4"]
    )

    assert cited_ids == ["chunk_fake_999"]
    assert risk is not None
    assert "hallucinated_chunk_references" in risk
