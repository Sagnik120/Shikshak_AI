"""The offline fallback must teach the requested lesson, not a canned one."""
import json
from unittest.mock import MagicMock, patch

import httpx

from modules.ai_agent_orchestration.src.adapters import gemini_adapter
from modules.ai_agent_orchestration.src.adapters.gemini_adapter import (
    GeminiLLMAdapter,
    SmartMockLLMAdapter,
)
from modules.ai_agent_orchestration.src.agents.assessment import AssessmentAgent
from modules.ai_agent_orchestration.src.agents.explainer import ExplainerAgent
from modules.ai_agent_orchestration.src.agents.planner import PlannerAgent
from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult
from modules.ai_agent_orchestration.src.schemas.lesson import LearnerConstraints, LessonNode

CONSTRAINTS = LearnerConstraints(level="beginner", language="en", time_budget_min=9)
NEWTON = [
    "An object at rest stays at rest unless acted upon by an unbalanced force. "
    "This tendency is called inertia. A passenger lurching forward when a bus brakes is an example.",
    "The net force equals mass times acceleration, F = m a. Force is measured in newtons.",
]


def test_topic_plan_is_about_the_topic_and_fills_the_budget():
    plan = PlannerAgent(SmartMockLLMAdapter()).plan_lesson(
        source_type="topic", constraints=CONSTRAINTS, topic="Photosynthesis"
    )
    assert all("Photosynthesis" in n.concept for n in plan.nodes)
    assert sum(n.est_minutes for n in plan.nodes) == 9


def test_document_plan_uses_the_documents_chapters():
    outline = {"filename": "newton.pdf", "chapters": ["Chapter 1: Inertia", "Chapter 2: Force and Acceleration"],
               "excerpts": NEWTON}
    plan = PlannerAgent(SmartMockLLMAdapter()).plan_lesson(
        source_type="document", constraints=CONSTRAINTS, document_outline=outline
    )
    assert [n.concept for n in plan.nodes] == ["Inertia", "Force and Acceleration"]
    assert plan.source == "document"


def test_segment_is_built_from_grounding_and_speech_safe():
    node = LessonNode(node_id="n1", concept="Inertia", depth="intro", est_minutes=3,
                      visual_type="diagram", checkpoint_question=True)
    seg = ExplainerAgent(SmartMockLLMAdapter()).generate_segment(node, CONSTRAINTS, grounding_chunks=NEWTON)
    assert "inertia" in seg.script_text.lower()
    assert "$" not in seg.script_text and "\\" not in seg.script_text
    assert seg.notes and seg.notes.key_points
    assert "Thermodynamics" not in seg.script_text


def test_question_targets_the_taught_concept():
    node = LessonNode(node_id="n1", concept="Inertia", depth="intro", est_minutes=3,
                      visual_type="diagram", checkpoint_question=True)
    q = QuestionerAgent(SmartMockLLMAdapter()).generate_question(node)
    assert q.node_id == "n1" and "Inertia" in q.question_text
    assert "Thermodynamics" not in json.dumps(q.model_dump())


def test_assessment_score_comes_from_history():
    history = [
        EvaluationResult(node_id="a", correct=False, partial_credit=0.0, confidence=1, feedback_text=""),
        EvaluationResult(node_id="b", correct=False, partial_credit=0.2, confidence=1, feedback_text=""),
    ]
    report = AssessmentAgent(SmartMockLLMAdapter()).generate_report("L1", history)
    assert report.score_pct == 10.0
    assert "Outstanding" not in report.narrative_feedback


def test_offline_misconception_is_never_invented():
    reply = SmartMockLLMAdapter().complete(
        [{"role": "system", "content": "Identify the misconception"}, {"role": "user", "content": "x"}]
    )
    assert json.loads(reply)["misconception_tag"] is None


def test_gemini_retries_a_rate_limit_then_succeeds(monkeypatch):
    monkeypatch.setattr(gemini_adapter.time, "sleep", lambda _s: None)
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"candidates": [{"content": {"parts": [{"text": '{"ok": 1}'}]}}]}
    limited = MagicMock(status_code=429, headers={"retry-after": "1"})
    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.side_effect = [limited, ok]
        out = GeminiLLMAdapter(api_key="k").complete([{"role": "user", "content": "hi"}])
    assert out == '{"ok": 1}'


def test_gemini_falls_back_offline_after_persistent_network_errors(monkeypatch):
    monkeypatch.setattr(gemini_adapter.time, "sleep", lambda _s: None)
    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("down")
        out = GeminiLLMAdapter(api_key="k").complete(
            [{"role": "system", "content": "You are a Lesson Planner."},
             {"role": "user", "content": "Generate a LessonPlan for topic: Kinematics"}]
        )
    assert "Kinematics" in out


def test_after_a_failed_call_gemini_is_skipped_for_a_while(monkeypatch):
    """Quota used up: the next steps go straight offline, no ~9 s of retries each."""
    monkeypatch.setattr(gemini_adapter.time, "sleep", lambda _s: None)
    with patch("httpx.Client") as client_cls:
        post = client_cls.return_value.__enter__.return_value.post
        post.side_effect = httpx.ConnectError("down")
        GeminiLLMAdapter(api_key="k").complete([{"role": "user", "content": "hi"}])
        calls = post.call_count
        GeminiLLMAdapter(api_key="k").complete([{"role": "user", "content": "hi"}])
        assert post.call_count == calls  # skipped during the cooldown
