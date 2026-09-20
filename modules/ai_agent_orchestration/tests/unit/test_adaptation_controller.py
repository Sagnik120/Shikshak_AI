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
    assert "partial credit" in decision.reason


def test_adaptation_controller_modify_misconception():
    decision = AdaptationController().decide(_ev(tag="foo"), [])
    assert decision.action == "MODIFY"
    assert "foo" in decision.reason


def test_adaptation_controller_first_failure():
    assert AdaptationController().decide(_ev(), []).action == "MODIFY"


def test_adaptation_controller_second_failure_still_modifies():
    """One more re-explanation before giving up on the current plan."""
    decision = AdaptationController().decide(_ev(), [_ev()])
    assert decision.action == "MODIFY"


def test_adaptation_controller_regenerate_third_failure():
    decision = AdaptationController().decide(_ev(), [_ev(), _ev()])
    assert decision.action == "REGENERATE"


def test_adaptation_controller_human_escalation_fourth_failure():
    decision = AdaptationController().decide(_ev(), [_ev(), _ev(), _ev()])
    assert decision.action == "HUMAN"


def test_partial_credit_does_not_prevent_escalation_after_regenerate():
    """Once we've re-planned, repeated near-misses still reach a human."""
    history = [_ev(partial=0.5), _ev(partial=0.5), _ev(partial=0.5)]
    decision = AdaptationController().decide(_ev(partial=0.5), history)
    assert decision.action == "HUMAN"


def test_failure_count_resets_after_a_correct_answer():
    history = [_ev(), _ev(), _ev(correct=True)]
    decision = AdaptationController().decide(_ev(), history)
    assert decision.action == "MODIFY"


def test_failures_on_other_nodes_are_ignored():
    history = [_ev(node_id="n2"), _ev(node_id="n3")]
    decision = AdaptationController().decide(_ev(node_id="n1"), history)
    assert decision.action == "MODIFY"
