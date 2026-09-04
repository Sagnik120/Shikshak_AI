from pathlib import Path
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LessonNode
from modules.ai_agent_orchestration.src.schemas.teaching import TeachingSegment

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

def load_mock(filename: str) -> str:
    with open(FIXTURES_DIR / "mock_llm_responses" / filename, "r", encoding="utf-8") as f:
        return f.read()

def test_questioner_valid_response():
    mock_resp = load_mock("questioner.json")
    adapter = FakeLLMAdapter(responses=[mock_resp])
    questioner = QuestionerAgent(adapter)
    
    node = LessonNode(node_id="node_1", concept="Intro", depth="intro", est_minutes=5, visual_type="image", checkpoint_question=True)
    segment = TeachingSegment(node_id="node_1", script_text="hello", language="English", visual_spec={"type": "image", "content": ""}, avatar_cue="neutral")
    
    event = questioner.generate_question(node=node, recent_segment=segment)
    
    assert event.node_id == "node_1"
    assert event.type == "mcq"
    assert len(event.options) == 3
