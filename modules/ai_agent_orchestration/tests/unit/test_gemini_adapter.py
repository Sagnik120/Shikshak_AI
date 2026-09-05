import json
import pytest
from unittest.mock import patch, MagicMock

from modules.ai_agent_orchestration.src.adapters.gemini_adapter import (
    SmartMockLLMAdapter,
    GeminiLLMAdapter,
    get_llm_adapter,
)
from modules.ai_agent_orchestration.src.schemas.lesson import LessonPlan
from modules.ai_agent_orchestration.src.schemas.teaching import TeachingSegment
from modules.ai_agent_orchestration.src.schemas.interaction import InteractionEvent
from modules.ai_agent_orchestration.src.schemas.assessment import AssessmentReport
from modules.ai_agent_orchestration.src.agents.base import BaseAgent


def test_smart_mock_adapter_planner_payload():
    adapter = SmartMockLLMAdapter()
    agent = BaseAgent(adapter)
    plan = agent.call_llm_json(
        system_prompt="You are a Lesson Planner.",
        user_prompt="Generate a LessonPlan for topic: Kinematics",
        response_model=LessonPlan,
    )
    assert isinstance(plan, LessonPlan)
    assert len(plan.nodes) >= 1
    assert plan.nodes[0].concept != ""


def test_smart_mock_adapter_explainer_payload():
    adapter = SmartMockLLMAdapter()
    agent = BaseAgent(adapter)
    segment = agent.call_llm_json(
        system_prompt="You are an Explainer Agent generating a TeachingSegment.",
        user_prompt="Explain concept with visual spec",
        response_model=TeachingSegment,
    )
    assert isinstance(segment, TeachingSegment)
    assert len(segment.script_text) > 0
    assert segment.visual_spec is not None


def test_smart_mock_adapter_questioner_payload():
    adapter = SmartMockLLMAdapter()
    agent = BaseAgent(adapter)
    event = agent.call_llm_json(
        system_prompt="You are a Questioner Agent generating an InteractionEvent.",
        user_prompt="Generate a checkpoint question for concept",
        response_model=InteractionEvent,
    )
    assert isinstance(event, InteractionEvent)
    assert event.type in ("mcq", "short_answer", "numeric")
    assert len(event.question_text) > 0


def test_smart_mock_adapter_assessment_payload():
    adapter = SmartMockLLMAdapter()
    agent = BaseAgent(adapter)
    report = agent.call_llm_json(
        system_prompt="You are an Assessment Agent generating an AssessmentReport.",
        user_prompt="Generate final assessment report",
        response_model=AssessmentReport,
    )
    assert isinstance(report, AssessmentReport)
    assert 0.0 <= report.score_pct <= 100.0


def test_gemini_adapter_fallback_when_no_api_key():
    adapter = GeminiLLMAdapter(api_key="")
    resp_str = adapter.complete([{"role": "user", "content": "Generate a LessonPlan"}])
    parsed = json.loads(resp_str)
    assert "lesson_id" in parsed or "nodes" in parsed


def test_gemini_adapter_fallback_on_network_error():
    adapter = GeminiLLMAdapter(api_key="mock_api_key")
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = Exception("Network unreachable")
        mock_client_cls.return_value = mock_client

        resp_str = adapter.complete([{"role": "user", "content": "Generate a TeachingSegment"}])
        parsed = json.loads(resp_str)
        assert "script_text" in parsed


def test_get_llm_adapter_factory():
    # When api_key is None and env is empty
    with patch.dict("os.environ", {}, clear=True):
        adapter = get_llm_adapter()
        assert isinstance(adapter, SmartMockLLMAdapter)

    # When api_key is provided explicitly
    adapter_with_key = get_llm_adapter(api_key="test_key_123")
    assert isinstance(adapter_with_key, GeminiLLMAdapter)
    assert adapter_with_key.api_key == "test_key_123"
