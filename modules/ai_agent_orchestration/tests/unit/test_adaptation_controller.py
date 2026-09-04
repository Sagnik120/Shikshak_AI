from modules.ai_agent_orchestration.src.agents.adaptation_controller import AdaptationController
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult

def test_adaptation_controller_allow_high_confidence():
    controller = AdaptationController()
    ev = EvaluationResult(node_id="n1", correct=True, confidence=0.8, partial_credit=0.0, feedback_text="")
    decision = controller.decide(ev, [])
    assert decision.action == "ALLOW"

def test_adaptation_controller_allow_low_confidence():
    controller = AdaptationController()
    ev = EvaluationResult(node_id="n1", correct=True, confidence=0.4, partial_credit=0.0, feedback_text="")
    decision = controller.decide(ev, [])
    assert decision.action == "ALLOW"

def test_adaptation_controller_modify_partial_credit():
    controller = AdaptationController()
    ev = EvaluationResult(node_id="n1", correct=False, confidence=0.5, partial_credit=0.5, feedback_text="")
    decision = controller.decide(ev, [])
    assert decision.action == "MODIFY"
    assert "partial credit" in decision.reason

def test_adaptation_controller_modify_misconception():
    controller = AdaptationController()
    ev = EvaluationResult(node_id="n1", correct=False, confidence=0.9, partial_credit=0.0, misconception_tag="foo", feedback_text="")
    decision = controller.decide(ev, [])
    assert decision.action == "MODIFY"
    assert "foo" in decision.reason

def test_adaptation_controller_first_failure():
    controller = AdaptationController()
    ev = EvaluationResult(node_id="n1", correct=False, confidence=0.9, partial_credit=0.0, feedback_text="")
    decision = controller.decide(ev, [])
    assert decision.action == "MODIFY"

def test_adaptation_controller_regenerate_second_failure():
    controller = AdaptationController()
    ev1 = EvaluationResult(node_id="n1", correct=False, confidence=0.9, partial_credit=0.0, feedback_text="")
    # The second failure on the same node
    ev2 = EvaluationResult(node_id="n1", correct=False, confidence=0.9, partial_credit=0.0, feedback_text="")
    decision = controller.decide(ev2, [ev1])
    assert decision.action == "REGENERATE"

def test_adaptation_controller_human_escalation_third_failure():
    controller = AdaptationController()
    ev1 = EvaluationResult(node_id="n1", correct=False, confidence=0.9, partial_credit=0.0, feedback_text="")
    ev2 = EvaluationResult(node_id="n1", correct=False, confidence=0.9, partial_credit=0.0, feedback_text="")
    ev3 = EvaluationResult(node_id="n1", correct=False, confidence=0.9, partial_credit=0.0, feedback_text="")
    decision = controller.decide(ev3, [ev1, ev2])
    assert decision.action == "HUMAN"
