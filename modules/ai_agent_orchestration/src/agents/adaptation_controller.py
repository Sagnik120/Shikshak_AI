from typing import List
from modules.ai_agent_orchestration.src.schemas.evaluation import EvaluationResult, AdaptationDecision

class AdaptationController:
    """
    Deterministic rule-based controller that yields AdaptationDecisions based on
    evaluation results and recent failure history.
    """
    
    def decide(
        self,
        current_eval: EvaluationResult,
        session_history: List[EvaluationResult]
    ) -> AdaptationDecision:
        node_id = current_eval.node_id
        
        # Count consecutive failures for this node
        failures = 0
        for ev in reversed(session_history):
            if ev.node_id == node_id and not ev.correct:
                failures += 1
            elif ev.node_id == node_id and ev.correct:
                break
                
        # Include current eval if not already in session_history (by identity)
        if not any(e is current_eval for e in session_history) and not current_eval.correct:
            failures += 1
            
        if current_eval.correct and current_eval.confidence >= 0.7:
            return AdaptationDecision(
                action="ALLOW",
                target_node_id=node_id,
                reason="Student answered correctly with high confidence."
            )
            
        # Allow correct answers even with low confidence if no other failure
        if current_eval.correct:
             return AdaptationDecision(
                action="ALLOW",
                target_node_id=node_id,
                reason="Student answered correctly."
            )

        # Handle repeated failures
        if failures >= 2:
            if failures >= 3:
                return AdaptationDecision(
                    action="HUMAN",
                    target_node_id=node_id,
                    reason="Repeated failures unresolved after regeneration. Escalating to human."
                )
            return AdaptationDecision(
                action="REGENERATE",
                target_node_id=node_id,
                reason="Student failed multiple times. Regenerating the lesson segment."
            )
            
        if current_eval.partial_credit > 0:
            return AdaptationDecision(
                action="MODIFY",
                target_node_id=node_id,
                reason="Student received partial credit. Modifying explanation with new analogy."
            )
            
        if current_eval.misconception_tag:
            return AdaptationDecision(
                action="MODIFY",
                target_node_id=node_id,
                reason=f"Misconception detected: {current_eval.misconception_tag}. Targeting misconception."
            )
            
        return AdaptationDecision(
            action="MODIFY",
            target_node_id=node_id,
            reason="Student answered incorrectly. Modifying explanation."
        )
