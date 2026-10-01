"""Rules: wrong -> MODIFY; wrong again on the concept -> REGENERATE (this
segment); more than 3 wrong answers in the lesson -> HUMAN."""
from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult


def _ev(correct=False, partial=0.0, confidence=0.9, tag=None, node_id="n1"):
    return EvaluationResult(
        node_id=node_id,
        correct=correct,
        confidence=confidence,
        partial_credit=partial,
        misconception_tag=tag,
        feedback_text="",
    )


def test_adaptation_controller_allow_high_confidence():
    decision = AdaptationController().decide(_ev(correct=True, confidence=0.8), [])
    assert decision.action == "ALLOW"


def test_adaptation_controller_allow_low_confidence():
    decision = AdaptationController().decide(_ev(correct=True, confidence=0.4), [])
    assert decision.action == "ALLOW"


def test_adaptation_controller_allows_strong_partial_credit():
    """Half credit means the core idea landed — keep teaching forward, don't re-teach."""
    decision = AdaptationController().decide(_ev(partial=0.5, confidence=0.5), [])
    assert decision.action == "ALLOW"
    assert "partial understanding" in decision.reason


def test_adaptation_controller_modifies_on_weak_partial_credit():
    decision = AdaptationController().decide(_ev(partial=0.2), [])
    assert decision.action == "MODIFY"


def test_adaptation_controller_modify_misconception():
    decision = AdaptationController().decide(_ev(tag="foo"), [])
    assert decision.action == "MODIFY"
    assert "foo" in decision.reason


def test_first_wrong_answer_re_explains():
    assert AdaptationController().decide(_ev(), []).action == "MODIFY"


def test_second_wrong_answer_on_the_concept_rebuilds_the_segment():
    assert AdaptationController().decide(_ev(), [_ev()]).action == "REGENERATE"


def test_third_wrong_answer_is_not_yet_more_than_three():
    assert AdaptationController().decide(_ev(), [_ev(), _ev()]).action == "REGENERATE"


def test_fourth_wrong_answer_in_the_lesson_goes_to_a_human():
    assert AdaptationController().decide(_ev(), [_ev(), _ev(), _ev()]).action == "HUMAN"


def test_wrong_answers_on_different_concepts_add_up_to_human():
    history = [_ev(node_id="n2"), _ev(node_id="n3"), _ev(node_id="n4")]
    assert AdaptationController().decide(_ev(node_id="n1"), history).action == "HUMAN"


def test_good_enough_partial_answers_never_count_as_wrong():
    history = [_ev(partial=0.5), _ev(partial=0.5), _ev(partial=0.5)]
    assert AdaptationController().decide(_ev(partial=0.5), history).action == "ALLOW"


def test_streak_resets_after_a_correct_answer():
    history = [_ev(), _ev(correct=True)]
    assert AdaptationController().decide(_ev(), history).action == "MODIFY"


def test_failures_on_other_nodes_do_not_start_a_streak():
    history = [_ev(node_id="n2"), _ev(node_id="n3")]
    assert AdaptationController().decide(_ev(node_id="n1"), history).action == "MODIFY"
