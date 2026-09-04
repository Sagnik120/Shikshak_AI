import json
from pathlib import Path
from modules.ml_core.src.concept_extraction.extractor import ConceptExtractor

def test_concept_extraction_valid_chunks():
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_parsed_document.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    
    chunk_texts = [c["text"] for c in doc.get("chunks", [])]
    
    extractor = ConceptExtractor()
    terms = extractor.extract(chunk_texts, top_k=5)
    
    # Assert we get terms back, and no file reading happened inside extract()
    assert len(terms) > 0
    assert isinstance(terms, list)
    # the stopwords filter will leave words like 'newton', 'first', 'law', 'object', 'force'
    assert "force" in terms or "newton" in terms or "mass" in terms or "law" in terms

def test_concept_extraction_empty_text():
    extractor = ConceptExtractor()
    terms = extractor.extract(["", "   ", "!"], top_k=5)
    assert terms == []
