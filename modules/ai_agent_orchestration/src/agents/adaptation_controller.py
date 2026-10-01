from typing import List

from modules.ai_agent_orchestration.src.schemas.evaluation import (
    AdaptationDecision,
    EvaluationResult,
)

# An answer at or above this credit shows enough understanding to move on, with
# the gap addressed in the rest of the segment rather than by re-teaching it.
REINFORCE_CREDIT = 0.5

# Wrong answers on the same concept, in a row, before its segment is rebuilt
# from scratch instead of re-explained.
REGENERATE_AFTER = 2

# More wrong answers than this in one lesson hands the learner to a human.
LESSON_WRONG_LIMIT = 3


def is_wrong(ev: EvaluationResult) -> bool:
    return not ev.correct and ev.partial_credit < REINFORCE_CREDIT


class AdaptationController:
    """Rule-based controller mapping an evaluation to the next pedagogical action.

    Per concept: wrong once -> re-explain it differently (MODIFY); wrong again
    -> rebuild that segment from scratch (REGENERATE). Across the lesson: more
    than LESSON_WRONG_LIMIT wrong answers -> hand over to a human (HUMAN).
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

        if not is_wrong(current_eval):
            # Close enough to continue: keep momentum and reinforce as we go.
            return AdaptationDecision(
                action="ALLOW",
                target_node_id=node_id,
                reason=(
                    "Student showed solid partial understanding "
                    f"({int(current_eval.partial_credit * 100)}%). Continuing and "
                    "reinforcing the missing detail."
                ),
            )

        past = [ev for ev in session_history if ev is not current_eval]
        lesson_wrong = 1 + sum(1 for ev in past if is_wrong(ev))
        if lesson_wrong > LESSON_WRONG_LIMIT:
            return AdaptationDecision(
                action="HUMAN",
                target_node_id=node_id,
                reason=(
                    f"{lesson_wrong} wrong answers in this lesson. "
                    "Escalating to a human teacher."
                ),
            )

        # Consecutive wrong answers on this concept, including this one; a
        # correct (or good-enough) answer on it resets the streak.
        streak = 1
        for ev in reversed(past):
            if ev.node_id != node_id:
                continue
            if not is_wrong(ev):
                break
            streak += 1

        if streak >= REGENERATE_AFTER:
            return AdaptationDecision(
                action="REGENERATE",
                target_node_id=node_id,
                reason="Still unclear after a re-explanation. Rebuilding this segment from scratch.",
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

        return AdaptationDecision(
            action="MODIFY",
            target_node_id=node_id,
            reason="Student answered incorrectly. Re-explaining with a new approach.",
        )
