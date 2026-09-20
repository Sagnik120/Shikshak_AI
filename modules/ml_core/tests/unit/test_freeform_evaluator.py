import json
from unittest.mock import patch

import pytest

from modules.ai_agent_orchestration.tests.fixtures.fake_llm_adapter import FakeLLMAdapter
from modules.ml_core.src.answer_evaluation.freeform_evaluator import (
    PASS_CREDIT,
    FreeformEvaluator,
)

SIM = "modules.ml_core.src.answer_evaluation.freeform_evaluator.get_similarity"
EXPECTED = "Mass is a measure of inertia."


@patch(SIM)
def test_freeform_confident_high(mock_sim):
    """A very close answer is accepted without spending an LLM call."""
    mock_sim.return_value = 0.9
    fake_llm = FakeLLMAdapter()

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Yes, mass is inertia.", EXPECTED)

    assert result.correct is True
    assert result.confidence == 0.9
    assert result.partial_credit == 1.0
    assert len(fake_llm.calls) == 0


@patch(SIM)
def test_freeform_confident_low(mock_sim):
    """A clearly unrelated answer is rejected without an LLM call."""
    mock_sim.return_value = 0.2
    fake_llm = FakeLLMAdapter()

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Wrong answer.", EXPECTED)

    assert result.correct is False
    assert result.confidence == pytest.approx(0.8)
    assert len(fake_llm.calls) == 0


@patch(SIM)
def test_freeform_ambiguous_llm_judge(mock_sim):
    """Mid-range similarity defers to the rubric judge."""
    mock_sim.return_value = 0.5
    fake_llm = FakeLLMAdapter(
        [json.dumps({"correct": False, "partial_credit": 0.5, "feedback_text": "Close."})]
    )

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "It is kinda like weight.", EXPECTED)

    assert result.correct is False
    assert result.partial_credit == 0.5
    assert result.feedback_text == "Close."
    assert len(fake_llm.calls) == 1


@patch(SIM)
def test_credit_above_the_pass_mark_counts_as_correct(mock_sim):
    """Models routinely return correct=false beside credit that clears the bar.

    Trusting that flag alone marks understood answers wrong and triggers
    needless re-teaching, so credit decides.
    """
    mock_sim.return_value = 0.5
    fake_llm = FakeLLMAdapter(
        [json.dumps({"correct": False, "partial_credit": 0.85, "feedback_text": "Good."})]
    )

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Mass resists acceleration.", EXPECTED)

    assert result.correct is True
    assert result.partial_credit == 0.85


@patch(SIM)
def test_correct_answer_never_reports_credit_below_the_pass_mark(mock_sim):
    mock_sim.return_value = 0.5
    fake_llm = FakeLLMAdapter(
        [json.dumps({"correct": True, "partial_credit": 0.1, "feedback_text": "Yes."})]
    )

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Mass resists acceleration.", EXPECTED)

    assert result.correct is True
    assert result.partial_credit >= PASS_CREDIT


@patch(SIM)
def test_credit_is_clamped_to_the_valid_range(mock_sim):
    mock_sim.return_value = 0.5
    fake_llm = FakeLLMAdapter(
        [json.dumps({"correct": True, "partial_credit": 4.2, "feedback_text": "Yes."})]
    )

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Mass resists acceleration.", EXPECTED)

    assert result.partial_credit == 1.0


@patch(SIM)
def test_fenced_json_is_parsed(mock_sim):
    """Models often wrap JSON in a markdown fence despite being told not to."""
    mock_sim.return_value = 0.5
    payload = json.dumps({"correct": True, "partial_credit": 0.9, "feedback_text": "Spot on."})
    fake_llm = FakeLLMAdapter([f"```json\n{payload}\n```"])

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Mass resists acceleration.", EXPECTED)

    assert result.correct is True
    assert result.feedback_text == "Spot on."


@patch(SIM)
def test_json_surrounded_by_prose_is_parsed(mock_sim):
    mock_sim.return_value = 0.5
    payload = json.dumps({"correct": True, "partial_credit": 0.8, "feedback_text": "Nice."})
    fake_llm = FakeLLMAdapter([f"Here is my grading:\n{payload}\nHope that helps."])

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Mass resists acceleration.", EXPECTED)

    assert result.correct is True
    assert result.partial_credit == 0.8


@patch(SIM)
def test_freeform_ambiguous_llm_malformed(mock_sim):
    """When the judge is unusable, fall back to the embedding signal.

    Failing the student outright on an infrastructure error would re-teach a
    concept they may well have understood, so the similarity score stands in
    and the low confidence marks the result as uncertain.
    """
    mock_sim.return_value = 0.5
    fake_llm = FakeLLMAdapter(["NOT JSON"])

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "It is kinda like weight.", EXPECTED)

    assert result.correct is False  # 0.5 is below the pass mark
    assert result.partial_credit == 0.5
    assert result.confidence == pytest.approx(0.4)


@patch(SIM)
def test_empty_answer_is_rejected_without_any_model_call(mock_sim):
    fake_llm = FakeLLMAdapter()

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "   ", EXPECTED)

    assert result.correct is False
    assert result.partial_credit == 0.0
    assert len(fake_llm.calls) == 0
    mock_sim.assert_not_called()


@patch(SIM, side_effect=RuntimeError("embedding model unavailable"))
def test_embedding_failure_falls_through_to_the_judge(mock_sim):
    """Losing the embedding model must not take grading down with it."""
    fake_llm = FakeLLMAdapter(
        [json.dumps({"correct": True, "partial_credit": 0.9, "feedback_text": "Correct."})]
    )

    result = FreeformEvaluator(fake_llm).evaluate("node_1", "Mass resists acceleration.", EXPECTED)

    assert result.correct is True
    assert len(fake_llm.calls) == 1
