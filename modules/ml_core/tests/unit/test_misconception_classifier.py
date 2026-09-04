import json
import pytest
from pathlib import Path
from modules.ml_core.src.misconception.classifier import MisconceptionClassifier
from modules.ml_core.src.misconception.taxonomy_loader import TaxonomyLoader
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

def test_misconception_valid_tag():
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "taxonomy_fixtures"
    loader = TaxonomyLoader(taxonomy_dir=str(fixture_dir))
    
    # Fake LLM returns a valid tag from our physics.json fixture
    llm_resp = json.dumps({"misconception_tag": "test_tag_mass_weight"})
    fake_llm = FakeLLMAdapter([llm_resp])
    
    classifier = MisconceptionClassifier(llm_adapter=fake_llm, taxonomy_loader=loader)
    tag = classifier.classify("Mass is weight", "Mass is inertia", "physics")
    
    assert tag == "test_tag_mass_weight"

def test_misconception_unknown_tag():
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "taxonomy_fixtures"
    loader = TaxonomyLoader(taxonomy_dir=str(fixture_dir))
    
    # Fake LLM hallucinates a tag not in our physics.json fixture
    llm_resp = json.dumps({"misconception_tag": "made_up_tag"})
    fake_llm = FakeLLMAdapter([llm_resp])
    
    classifier = MisconceptionClassifier(llm_adapter=fake_llm, taxonomy_loader=loader)
    tag = classifier.classify("Mass is weight", "Mass is inertia", "physics")
    
    assert tag is None

def test_misconception_no_taxonomy():
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "taxonomy_fixtures"
    loader = TaxonomyLoader(taxonomy_dir=str(fixture_dir))
    
    # Try classifying a subject we have no taxonomy for (e.g. math)
    fake_llm = FakeLLMAdapter([]) # Shouldn't be called
    classifier = MisconceptionClassifier(llm_adapter=fake_llm, taxonomy_loader=loader)
    tag = classifier.classify("2+2=5", "2+2=4", "math")
    
    assert tag is None
    assert len(fake_llm.calls) == 0
