"""Human-escalation lifecycle and "learn this again", in one place.

A lesson that escalates PAUSES at the stuck concept (it is never taught on
silently). From there the learner can:

* continue  -> re-teach the same concept, fresh explanation; a fresh
               wrong-answer count only WHILE that concept is re-taught —
               afterwards the whole lesson's count applies again
* skip      -> move past it (the count keeps going); marked "needs review"
* relearn   -> re-teach a skipped concept on its own (fresh count while it
               is taught), then return to where the lesson was

A lesson is only COMPLETED when every concept is mastered or watched. If it
reaches the end with concepts to review, it waits at "N to review".

Nothing is deleted: every escalation keeps its full history.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.backend.src.db.models import Escalation, Lesson, LessonNodeRow, utcnow
from modules.backend.src.services import lesson_service

OPEN_STATES = ("open", "continued")


class EscalationError(ValueError):
    """The requested action doesn't apply to the lesson's current state."""


def current_node_row(db: Session, lesson: Lesson) -> Optional[LessonNodeRow]:
    nodes = sorted(lesson.nodes, key=lambda n: n.position)
    if not nodes or lesson.current_node_index >= len(nodes):
        return None
    return nodes[lesson.current_node_index]


def open_escalation(db: Session, lesson: Lesson, node_id: str, concept: str, reason: str) -> Escalation:
    esc = Escalation(lesson_id=lesson.id, user_id=lesson.user_id, node_id=node_id,
                     concept=concept or node_id, reason=reason, status="open")
    db.add(esc)
    lesson.status = "escalated"
    lesson.fsm_state = "HUMAN_ESCALATION"
    db.flush()
    return esc


def active_escalation(db: Session, lesson: Lesson) -> Optional[Escalation]:
    return db.scalars(
        select(Escalation)
        .where(Escalation.lesson_id == lesson.id, Escalation.status.in_(OPEN_STATES))
        .order_by(Escalation.opened_at.desc())
    ).first()


def escalations_for(db: Session, lesson: Lesson) -> list[Escalation]:
    return list(db.scalars(
        select(Escalation).where(Escalation.lesson_id == lesson.id).order_by(Escalation.opened_at.asc())
    ).all())


def as_dict(esc: Optional[Escalation]) -> Optional[dict]:
    if esc is None:
        return None
    return {
        "id": esc.id,
        "lesson_id": esc.lesson_id,
        "node_id": esc.node_id,
        "concept": esc.concept,
        "status": esc.status,
        "reason": esc.reason,
        "resolution": esc.resolution,
        "mentor_notified": esc.mentor_notified,
        "opened_at": esc.opened_at.isoformat(),
        "continued_at": esc.continued_at.isoformat() if esc.continued_at else None,
        "closed_at": esc.closed_at.isoformat() if esc.closed_at else None,
    }


def _require_paused(db: Session, lesson: Lesson) -> Escalation:
    esc = active_escalation(db, lesson)
    if lesson.status != "escalated" or esc is None or esc.status != "open":
        raise EscalationError("This lesson isn't paused for a mentor.")
    return esc


def continue_lesson(db: Session, lesson: Lesson) -> Escalation:
    """Re-teach the stuck concept from scratch, with a fresh wrong-answer count."""
    esc = _require_paused(db, lesson)
    esc.status = "continued"
    esc.continued_at = utcnow()
    lesson.status = "in_progress"
    lesson.history_reset_at = utcnow()
    lesson_service.begin_node_explanation(db, lesson, esc.node_id)  # sets fsm EXPLAIN
    node = lesson_service.get_node(db, lesson, esc.node_id)
    if node is not None:
        node.status = "teaching"
    lesson_service.log_event(db, lesson, "escalation_continued", node_id=esc.node_id)
    db.flush()
    return esc


def skip_concept(db: Session, lesson: Lesson) -> Escalation:
    """Move past the stuck concept; it stays flagged for review."""
    esc = _require_paused(db, lesson)
    now = utcnow()
    esc.status = "skipped"
    esc.closed_at = now
    esc.resolution = "Skipped by the learner — marked for review."
    node = lesson_service.get_node(db, lesson, esc.node_id)
    if node is not None:
        node.status = "skipped"
        node.review_note = "needs review"
        node.completed_at = node.completed_at or now
    lesson.status = "in_progress"
    point = lesson.resume_point
    if point and point.get("node_id") == esc.node_id:
        # Skipping a concept that was being relearned: go back to where the
        # lesson was, not on to whatever follows the relearned concept.
        lesson.resume_point = None
        lesson.current_node_index = point.get("return_index", len(lesson.nodes))
        lesson.fsm_state = point.get("return_fsm") or "EXPLAIN"
    else:
        lesson.current_node_index = (node.position + 1) if node is not None else lesson.current_node_index + 1
        lesson.fsm_state = "EXPLAIN"
    lesson.history_reset_at = None  # skipping never resets the wrong-answer count
    lesson_service.log_event(db, lesson, "escalation_skipped", node_id=esc.node_id)
    db.flush()
    return esc


def relearn_concept(db: Session, lesson: Lesson, node_id: str) -> LessonNodeRow:
    """Re-teach one skipped concept, then return to where the lesson was."""
    if lesson.status not in ("completed", "in_progress"):
        raise EscalationError("Finish or continue the paused concept first.")
    if lesson.resume_point:
        raise EscalationError("Another concept is already being relearned in this lesson.")
    node = lesson_service.get_node(db, lesson, node_id)
    if node is None:
        raise EscalationError("Concept not found.")
    if node.status != "skipped":
        raise EscalationError("Only concepts you skipped can be learned again.")

    lesson.resume_point = {
        "node_id": node_id,
        "return_index": lesson.current_node_index,
        "return_status": lesson.status,
        "return_fsm": lesson.fsm_state,
    }
    lesson.current_node_index = node.position
    lesson.status = "in_progress"
    lesson.history_reset_at = utcnow()
    lesson_service.begin_node_explanation(db, lesson, node_id)  # sets fsm EXPLAIN
    node.status = "teaching"
    node.completed_at = None
    lesson_service.log_event(db, lesson, "concept_relearn_started", node_id=node_id)
    db.flush()
    return node


def on_node_closed(db: Session, lesson: Lesson, node: LessonNodeRow) -> Optional[Escalation]:
    """Update escalation history once the lesson moves past a node.

    Returns an escalation that has just been RESOLVED (the mentor gets one
    "no action needed" note), else None.
    """
    mastered = node.status == "mastered"
    now = utcnow()
    resolved = None

    continued = db.scalars(
        select(Escalation).where(
            Escalation.lesson_id == lesson.id, Escalation.node_id == node.node_id,
            Escalation.status == "continued",
        )
    ).all()
    for esc in continued:
        esc.closed_at = now
        if mastered:
            esc.status, esc.resolution = "resolved", "Mastered by the learner after continuing."
            node.review_note = "after help"
            resolved = esc
        else:
            esc.status, esc.resolution = "closed", "Moved on without mastering it — marked for review."
            node.review_note = "needs review"

    relearning = (lesson.resume_point or {}).get("node_id") == node.node_id
    if relearning:
        if mastered:
            node.review_note = "after review"
            for esc in db.scalars(
                select(Escalation).where(
                    Escalation.lesson_id == lesson.id, Escalation.node_id == node.node_id,
                    Escalation.status.in_(("skipped", "closed")),
                )
            ).all():
                esc.status, esc.closed_at = "resolved", now
                esc.resolution = "Mastered later with “Learn this again”."
                resolved = resolved or esc
        else:
            node.review_note = "needs review"
    elif node.status == "skipped" and node.review_note is None and node.attempts > 0:
        node.review_note = "needs review"  # moved on without mastering it
    db.flush()
    return resolved


def concepts_to_review(lesson: Lesson) -> list[LessonNodeRow]:
    """Concepts the learner moved past without mastering — not done yet."""
    return [n for n in sorted(lesson.nodes, key=lambda x: x.position) if n.status == "skipped"]


def mark_review_pending(lesson: Lesson) -> None:
    """Reached the end with concepts to review: NOT completed."""
    lesson.status = "in_progress"
    lesson.fsm_state = "REVIEW_PENDING"
    lesson.current_node_index = len(lesson.nodes)


def finish_relearn(lesson: Lesson) -> Optional[dict]:
    """Clear the relearn marker; return where the lesson should go back to."""
    point = lesson.resume_point
    lesson.resume_point = None
    return point
