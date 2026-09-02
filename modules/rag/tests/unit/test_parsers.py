"""Unit tests for document parsers and structure extractors."""

from modules.rag.src.parsing.parser import parse_document, extract_raw_sections
from modules.rag.src.parsing.txt_parser import parse_text_or_markdown
from modules.rag.src.parsing.structure import detect_language, extract_key_terms_tfidf


def test_markdown_heading_extraction():
    """Test that Markdown headings are parsed as chapters and section titles."""
    content = """# Introduction to Kinematics
Kinematics is the branch of mechanics concerned with the motion of objects.

## Speed and Velocity
Speed is a scalar quantity, while velocity is a vector quantity.

## Acceleration
Acceleration is the rate of change of velocity over time.
"""
    sections, chapters = parse_text_or_markdown(content)
    assert len(sections) == 3
    assert "Introduction to Kinematics" in chapters
    assert "Speed and Velocity" in chapters
    assert "Acceleration" in chapters
    assert sections[1].section_title == "Speed and Velocity"


def test_short_single_paragraph_document():
    """Edge Case §5.1: 1-paragraph upload creates exactly one valid section."""
    short_text = "Photosynthesis is the process by which green plants convert sunlight into chemical energy."
    doc = parse_document(
        file_bytes=short_text.encode("utf-8"),
        filename="short_notes.txt",
        mime_type="text/plain"
    )

    assert doc.document_id is not None
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text.strip() == short_text
    assert doc.chunks[0].page_or_slide is None


def test_no_structure_wall_of_text():
    """Edge Case §5.1: Document with no headings falls back gracefully."""
    wall_of_text = """This is a paragraph about thermodynamics without any headings or markdown tags.
    
Here is a second paragraph explaining entropy and heat transfer in isolated systems."""
    doc = parse_document(
        file_bytes=wall_of_text.encode("utf-8"),
        filename="unstructured.txt",
        mime_type="text/plain"
    )

    assert doc.detected_structure.chapters == []
    assert len(doc.chunks) >= 1
    assert all(c.section_title is None for c in doc.chunks)


def test_tfidf_key_terms_extraction():
    """Test TF-IDF extracts relevant domain keywords."""
    text = """
    Quantum mechanics is a fundamental theory in physics that provides a description of the physical
    properties of nature at the scale of atoms and subatomic particles. It is the foundation of all
    quantum physics including quantum chemistry, quantum field theory, quantum technology, and quantum
    information science. Wave-particle duality and uncertainty principle are key concepts in quantum physics.
    """
    key_terms = extract_key_terms_tfidf(text, top_n=5)
    assert len(key_terms) > 0
    assert any("quantum" in term.lower() or "physics" in term.lower() for term in key_terms)


def test_language_detection_hindi():
    """Test Devanagari script detection for Hindi."""
    hindi_text = "ओम का नियम कहता है कि एक चालक में प्रवाहित धारा उसके सिरों के बीच विभवांतर के समानुपाती होती है।"
    lang = detect_language(hindi_text)
    assert lang == "hi"


def test_language_detection_english():
    """Test English language detection."""
    english_text = "Newton's first law states that an object at rest will remain at rest unless acted upon by a force."
    lang = detect_language(english_text)
    assert lang == "en"
