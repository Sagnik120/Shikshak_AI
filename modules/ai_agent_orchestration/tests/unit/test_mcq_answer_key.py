"""An MCQ's answer key must be one of its options, or every learner is marked wrong.

Live Gemini wrote an explanation as expected_concept, so the exact-match MCQ
grader failed correct answers — which drove MODIFY/REGENERATE/HUMAN for
learners who were right.
"""
import json

from modules.ai_agent_orchestration.src.agents.questioner import QuestionerAgent
from modules.ai_agent_orchestration.src.schemas.lesson import LessonNode
from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter

NODE = LessonNode(node_id="n1", concept="Force pairs", depth="core", est_minutes=3,
                  visual_type="diagram", checkpoint_question=True)
OPTIONS = ["The apple pulls up with the exact same amount of force.",
           "The apple does not pull up on the Earth at all."]


def _mcq(key: str) -> str:
    return json.dumps({"node_id": "n1", "question_text": "How hard does the apple pull back?",
                       "type": "mcq", "options": OPTIONS, "expected_concept": key})


def test_verbatim_key_is_kept():
    q = QuestionerAgent(FakeLLMAdapter([_mcq(OPTIONS[0])])).generate_question(NODE)
    assert q.type == "mcq" and q.expected_concept == OPTIONS[0]


def test_key_differing_only_in_punctuation_is_aligned_to_the_option():
    q = QuestionerAgent(FakeLLMAdapter([_mcq("the apple pulls up with the exact same amount of force")])) \
        .generate_question(NODE)
    assert q.expected_concept == OPTIONS[0]


def test_explanation_key_triggers_one_retry():
    adapter = FakeLLMAdapter([_mcq("Forces come in equal and opposite pairs."), _mcq(OPTIONS[0])])
    q = QuestionerAgent(adapter).generate_question(NODE)
    assert q.type == "mcq" and q.expected_concept == OPTIONS[0]
    assert len(adapter.calls) == 2


def test_unfixable_key_becomes_a_free_text_question():
    bad = _mcq("Forces come in equal and opposite pairs.")
    q = QuestionerAgent(FakeLLMAdapter([bad, bad])).generate_question(NODE)
    assert q.type == "short_answer" and q.options == []
    assert "equal and opposite" in q.expected_concept
