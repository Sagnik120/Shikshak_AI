import json
from pathlib import Path
from modules.ml_core.src.service import MLCoreService

def test_rag_boundary_concept_extractor():
    service = MLCoreService() # LLMAdapter not strictly needed for just concepts
    
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_parsed_document.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
        
    chunk_texts = [c["text"] for c in doc.get("chunks", [])]
    
    key_terms = service.extract_concepts(chunk_texts)
    
    assert isinstance(key_terms, list)
    assert len(key_terms) > 0
