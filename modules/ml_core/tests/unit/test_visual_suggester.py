import json
from modules.ml_core.src.visual_suggestion.suggester import VisualTypeSuggester
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

def test_visual_suggester_rule_table_first():
    fake_llm = FakeLLMAdapter() # LLM should not be called
    suggester = VisualTypeSuggester(llm_adapter=fake_llm)
    
    # "math" maps to "equation" via rules.py
    v_type = suggester.suggest("math", "calculus")
    assert v_type == "equation"
    assert len(fake_llm.calls) == 0

    # "algorithm" concept maps to "code"
    v_type2 = suggester.suggest("computer science", "sorting algorithm")
    assert v_type2 == "code"
    assert len(fake_llm.calls) == 0

def test_visual_suggester_llm_fallback_ambiguous():
    llm_resp = json.dumps({"visual_type": "timeline"})
    fake_llm = FakeLLMAdapter([llm_resp])
    suggester = VisualTypeSuggester(llm_adapter=fake_llm)
    
    # "unknown_subject" doesn't hit rules, LLM provides timeline
    v_type = suggester.suggest("unknown_subject", "unknown_concept")
    
    assert v_type == "timeline"
    assert len(fake_llm.calls) == 1

def test_visual_suggester_llm_fallback_invalid_enum():
    # LLM hallucinates an invalid visual type not in Contract
    llm_resp = json.dumps({"visual_type": "hologram"})
    fake_llm = FakeLLMAdapter([llm_resp])
    suggester = VisualTypeSuggester(llm_adapter=fake_llm)
    
    v_type = suggester.suggest("unknown_subject", "unknown_concept")
    
    # Should fallback to 'image'
    assert v_type == "image"
