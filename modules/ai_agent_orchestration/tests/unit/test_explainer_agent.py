import json
from pathlib import Path
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints, LessonNode

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def load_mock(filename: str) -> str:
    with open(FIXTURES_DIR / "mock_llm_responses" / filename, "r", encoding="utf-8") as f:
        return f.read()

def test_explainer_valid_response():
    mock_resp = load_mock("explainer.json")
    adapter = FakeLLMAdapter(responses=[mock_resp])
    explainer = ExplainerAgent(adapter)
    
    constraints = LearnerConstraints(level="beginner", language="English", time_budget_min=15, style="visual")
    node = LessonNode(node_id="node_1", concept="Intro", depth="intro", est_minutes=5, visual_type="image", checkpoint_question=True)
    
    segment = explainer.generate_segment(node=node, constraints=constraints)
    
    assert segment.node_id == "node_1"
    assert segment.avatar_cue == "neutral"
    
def test_explainer_with_grounding_chunks():
    mock_resp = load_mock("explainer.json")
    adapter = FakeLLMAdapter(responses=[mock_resp])
    explainer = ExplainerAgent(adapter)
    
    constraints = LearnerConstraints(level="beginner", language="English", time_budget_min=15, style="visual")
    node = LessonNode(node_id="node_1", concept="Intro", depth="intro", est_minutes=5, visual_type="image", checkpoint_question=True)
    
    # Passing raw strings to simulate chunks
    segment = explainer.generate_segment(node=node, constraints=constraints, grounding_chunks=["chunk1_text", "chunk2_text"])
    
    assert segment.node_id == "node_1"
    assert "chunk1_text" in adapter.calls[0][1]["content"]
