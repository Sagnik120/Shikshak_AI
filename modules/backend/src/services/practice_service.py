"""Practice questions: revision with the questions a lesson already asked.

Read-only with respect to learning: attempts go to their own table and never
touch the lesson's interactions, node mastery, score, report, escalation
count or learner profile. Multiple-choice is checked locally for free; a
written answer costs one grading call.
"""
import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.backend.src.db.models import Interaction, Lesson, PracticeAttempt


class PracticeError(ValueError):
    pass


def _norm(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"^\(?\s*[a-d0-9]\s*[\).:-]\s+", "", text)
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def practice_set(db: Session, lesson: Lesson, user_id: str) -> list[dict]:
    """Every graded question in the lesson, once each, wrong ones first."""
    concepts = {n.node_id: n.concept for n in lesson.nodes}
    graded = db.scalars(
        select(Interaction)
        .where(Interaction.lesson_id == lesson.id, Interaction.correct.is_not(None))
        .order_by(Interaction.asked_at.asc())
    ).all()

    attempts = db.scalars(
        select(PracticeAttempt)
        .where(PracticeAttempt.lesson_id == lesson.id, PracticeAttempt.user_id == user_id)
        .order_by(PracticeAttempt.answered_at.asc())
    ).all()
    last_practice = {a.interaction_id: a for a in attempts}

    seen, items = set(), []
    for q in graded:
        key = (q.node_id, _norm(q.question_text))
        if key in seen:
            continue
        seen.add(key)
        practice = last_practice.get(q.id)
        items.append({
            "interaction_id": q.id,
            "node_id": q.node_id,
            "concept": concepts.get(q.node_id, q.node_id),
            "question_text": q.question_text,
            "type": q.question_type,
            "options": list(q.options or []),
            "your_lesson_answer": q.raw_answer,
            "lesson_correct": bool(q.correct),
            "needs_practice": not q.correct,
            "last_practice": None if practice is None else {
                "correct": practice.correct, "answer": practice.answer,
                "answered_at": practice.answered_at.isoformat(),
            },
        })
    # Wrong in the lesson first, then in lesson order.
    items.sort(key=lambda it: (not it["needs_practice"],))
    return items


def grade(db: Session, lesson: Lesson, user_id: str, interaction_id: str, answer: str) -> dict:
    question: Optional[Interaction] = db.get(Interaction, interaction_id)
    if question is None or question.lesson_id != lesson.id or question.correct is None:
        raise PracticeError("That question isn't available for practice.")
    answer = (answer or "").strip()
    if not answer:
        raise PracticeError("Type or pick an answer first.")

    if question.question_type == "mcq":
        correct = _norm(answer) == _norm(question.expected_concept)
        feedback = "Correct!" if correct else "Not quite."
        model_answer = question.expected_concept
    else:
        from modules.ai_agent_orchestration.src.schemas.interaction import StudentResponse
        from modules.backend.src.integrations.container import services

        evaluator = services["ml_core_service"].evaluator
        result = evaluator.evaluate(
            StudentResponse(node_id=question.node_id, raw_answer=answer,
                            response_type=question.question_type, response_time_sec=0.0),
            question.expected_concept,
        )
        correct, feedback = bool(result.correct), result.feedback_text or ""
        model_answer = question.expected_concept

    db.add(PracticeAttempt(user_id=user_id, lesson_id=lesson.id, interaction_id=question.id,
                           answer=answer[:4000], correct=correct, feedback_text=feedback))
    db.flush()
    return {"correct": correct, "feedback_text": feedback, "model_answer": model_answer}
