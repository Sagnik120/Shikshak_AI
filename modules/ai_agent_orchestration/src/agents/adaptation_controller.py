from typing import List

from modules.ai_agent_orchestration.src.schemas.evaluation import (
    AdaptationDecision,
    EvaluationResult,
)

# An answer at or above this credit shows enough understanding to move on, with
# the gap addressed in the next segment rather than by re-teaching the node.
REINFORCE_CREDIT = 0.5

# Attempts on a single node before each escalation rung.
REGENERATE_AFTER = 3
HUMAN_AFTER = 4


class AdaptationController:
    """Rule-based controller mapping an evaluation to the next pedagogical action.

    The ladder is: re-explain differently (MODIFY) -> re-plan the remaining
    lesson (REGENERATE) -> hand over to a human (HUMAN). Escalation is driven by
    attempts on the same node, so a learner who is close is never escalated.
    """

    def decide(
        self,
        current_eval: EvaluationResult,
        session_history: List[EvaluationResult],
    ) -> AdaptationDecision:
        node_id = current_eval.node_id

        if current_eval.correct:
            return AdaptationDecision(
                action="ALLOW",
                target_node_id=node_id,
                reason=(
                    "Student answered correctly with high confidence."
                    if current_eval.confidence >= 0.7
                    else "Student answered correctly."
                ),
            )

        # Count consecutive unsuccessful attempts on this node, including the
        # current one, resetting whenever the node was previously answered.
        failures = 1
        for past in reversed(session_history):
            if past.node_id != node_id or past is current_eval:
                continue
            if past.correct:
                break
            failures += 1

        # Close enough to continue: keep momentum and reinforce as we go, rather
        # than re-teaching a node the student has largely understood.
        if current_eval.partial_credit >= REINFORCE_CREDIT and failures < REGENERATE_AFTER:
            return AdaptationDecision(
                action="ALLOW",
                target_node_id=node_id,
                reason=(
                    "Student showed solid partial understanding "
                    f"({int(current_eval.partial_credit * 100)}%). Continuing and "
                    "reinforcing the missing detail in the next segment."
                ),
            )

        if failures >= HUMAN_AFTER:
            return AdaptationDecision(
                action="HUMAN",
                target_node_id=node_id,
                reason="Repeated failures unresolved after regeneration. Escalating to human.",
            )

        if failures >= REGENERATE_AFTER:
            return AdaptationDecision(
                action="REGENERATE",
                target_node_id=node_id,
                reason="Student failed multiple times. Regenerating the lesson segment.",
            )

        if current_eval.misconception_tag:
            return AdaptationDecision(
                action="MODIFY",
                target_node_id=node_id,
                reason=(
                    f"Misconception detected: {current_eval.misconception_tag}. "
                    "Targeting misconception."
                ),
            )

        if current_eval.partial_credit > 0:
            return AdaptationDecision(
                action="MODIFY",
                target_node_id=node_id,
                reason="Student received partial credit. Modifying explanation with new analogy.",
            )

        return AdaptationDecision(
            action="MODIFY",
            target_node_id=node_id,
            reason="Student answered incorrectly. Modifying explanation.",
        )
