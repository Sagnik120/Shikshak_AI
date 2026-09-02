"""Unit tests verifying ParsedDocument and Chunk strictly match Contract.md §4."""

import json
from modules.rag.src.models import ParsedDocument, Chunk, DetectedStructure


def test_chunk_contract_schema():
    """Verify Chunk has exact fields matching Contract §4."""
    chunk = Chunk(
        chunk_id="chunk_0001",
        text="Sample text for testing.",
        section_title="Introduction",
        page_or_slide=1,
        embedding_ref="doc123#chunk_0001"
    )

    data = chunk.model_dump()
    expected_keys = {"chunk_id", "text", "section_title", "page_or_slide", "embedding_ref"}
    assert set(data.keys()) == expected_keys
    assert data["chunk_id"] == "chunk_0001"
    assert data["page_or_slide"] == 1


def test_chunk_optional_fields_nullable():
    """Verify section_title and page_or_slide can be None."""
    chunk = Chunk(
        chunk_id="chunk_0002",
        text="Text with null metadata."
    )
    data = chunk.model_dump()
    assert data["section_title"] is None
    assert data["page_or_slide"] is None
    assert data["embedding_ref"] == ""


def test_parsed_document_contract_schema():
    """Verify ParsedDocument root schema matches Contract §4 exactly."""
    doc = ParsedDocument(
        document_id="doc_abc123",
        source_lang="en",
        chunks=[
            Chunk(
                chunk_id="chunk_0001",
                text="Ohm's law states that V = IR.",
                section_title="Ohm's Law",
                page_or_slide=4,
                embedding_ref="doc_abc123#chunk_0001"
            )
        ],
        detected_structure=DetectedStructure(
            chapters=["Electricity", "Ohm's Law"],
            key_terms=["voltage", "current", "resistance"]
        )
    )

    data = doc.model_dump()
    expected_top_keys = {"document_id", "source_lang", "chunks", "detected_structure"}
    assert set(data.keys()) == expected_top_keys
    assert set(data["detected_structure"].keys()) == {"chapters", "key_terms"}
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["chunk_id"] == "chunk_0001"


def test_parsed_document_json_serialization():
    """Ensure ParsedDocument serializes to standard JSON matching Contract §4 snippet."""
    doc = ParsedDocument(
        document_id="test_doc",
        source_lang="hi",
        chunks=[],
        detected_structure=DetectedStructure(chapters=[], key_terms=[])
    )
    json_str = doc.model_dump_json()
    parsed_back = json.loads(json_str)
    assert parsed_back["document_id"] == "test_doc"
    assert parsed_back["source_lang"] == "hi"
    assert isinstance(parsed_back["chunks"], list)
    assert isinstance(parsed_back["detected_structure"]["chapters"], list)
    assert isinstance(parsed_back["detected_structure"]["key_terms"], list)
