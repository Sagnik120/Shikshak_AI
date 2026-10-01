"""Pause -> continue / skip -> relearn, and practice that never touches the lesson."""
import pytest

from modules.backend.src.db.models import Interaction, Lesson, LessonNodeRow, User
from modules.backend.src.services import escalation_service as esc_svc
from modules.backend.src.services import lesson_service, practice_service


def _lesson(db) -> Lesson:
    user = User(email="p@example.com", full_name="Pat Learner", password_hash="x", is_verified=True)
    db.add(user)
    db.flush()
    lesson = Lesson(user_id=user.id, title="Forces", status="in_progress", current_node_index=1,
                    plan_json={"nodes": []})
    db.add(lesson)
    db.flush()
    for i, concept in enumerate(["Inertia", "F = ma", "Action-reaction"]):
        db.add(LessonNodeRow(lesson_id=lesson.id, node_id=f"n{i}", position=i, concept=concept,
                             status="mastered" if i == 0 else "pending"))
    db.flush()
    db.refresh(lesson)
    return lesson


def _pause(db, lesson):
    return esc_svc.open_escalation(db, lesson, "n1", "F = ma", "4 wrong answers")


def test_escalation_pauses_the_lesson(db):
    lesson = _lesson(db)
    esc = _pause(db, lesson)
    assert lesson.status == "escalated" and esc.status == "open"
    assert esc_svc.active_escalation(db, lesson).id == esc.id


def test_continue_reteaches_the_same_concept_with_a_fresh_count(db):
    lesson = _lesson(db)
    _pause(db, lesson)
    esc = esc_svc.continue_lesson(db, lesson)
    assert esc.status == "continued" and lesson.status == "in_progress"
    assert lesson.current_node_index == 1 and lesson.fsm_state == "EXPLAIN"
    assert lesson.history_reset_at is not None


def test_continue_then_mastered_resolves_and_marks_after_help(db):
    lesson = _lesson(db)
    _pause(db, lesson)
    esc_svc.continue_lesson(db, lesson)
    node = lesson_service.get_node(db, lesson, "n1")
    node.status = "mastered"
    resolved = esc_svc.on_node_closed(db, lesson, node)
    assert resolved is not None and resolved.status == "resolved"
    assert node.review_note == "after help"


def test_continue_then_moved_on_unmastered_closes_for_review(db):
    lesson = _lesson(db)
    _pause(db, lesson)
    esc_svc.continue_lesson(db, lesson)
    node = lesson_service.get_node(db, lesson, "n1")
    node.status = "skipped"
    assert esc_svc.on_node_closed(db, lesson, node) is None
    assert node.review_note == "needs review"
    assert esc_svc.escalations_for(db, lesson)[0].status == "closed"


def test_skip_moves_on_flags_for_review_and_keeps_the_count(db):
    lesson = _lesson(db)
    _pause(db, lesson)
    esc = esc_svc.skip_concept(db, lesson)
    node = lesson_service.get_node(db, lesson, "n1")
    assert esc.status == "skipped" and node.status == "skipped" and node.review_note == "needs review"
    assert lesson.status == "in_progress" and lesson.current_node_index == 2
    assert lesson.history_reset_at is None  # skipping never resets the wrong-answer count


def test_skipped_concept_is_not_counted_as_done(db):
    lesson = _lesson(db)
    _pause(db, lesson)
    esc_svc.skip_concept(db, lesson)
    summary = lesson_service.lesson_summary(db, lesson)
    assert summary["nodes_completed"] == 1 and summary["to_review"] == 1
    assert [n.node_id for n in esc_svc.concepts_to_review(lesson)] == ["n1"]


def test_reaching_the_end_with_concepts_to_review_is_not_completed(db):
    lesson = _lesson(db)
    _pause(db, lesson)
    esc_svc.skip_concept(db, lesson)
    esc_svc.mark_review_pending(lesson)
    summary = lesson_service.lesson_summary(db, lesson)
    assert lesson.status == "in_progress" and summary["review_pending"] and summary["to_review"] == 1


def test_skip_during_relearn_returns_to_where_the_lesson_was(db):
    lesson = _lesson(db)
    _pause(db, lesson)
    esc_svc.skip_concept(db, lesson)          # n1 to review, lesson at n2
    esc_svc.relearn_concept(db, lesson, "n1")  # back to n1 for a moment
    esc_svc.open_escalation(db, lesson, "n1", "F = ma", "4 wrong again")
    esc_svc.skip_concept(db, lesson)
    assert lesson.current_node_index == 2 and lesson.resume_point is None


def test_actions_are_refused_when_not_paused(db):
    lesson = _lesson(db)
    with pytest.raises(esc_svc.EscalationError):
        esc_svc.continue_lesson(db, lesson)
    with pytest.raises(esc_svc.EscalationError):
        esc_svc.skip_concept(db, lesson)


def test_relearn_only_skipped_concepts_and_returns_afterwards(db):
    lesson = _lesson(db)
    with pytest.raises(esc_svc.EscalationError):
        esc_svc.relearn_concept(db, lesson, "n0")  # mastered, not skipped
    _pause(db, lesson)
    with pytest.raises(esc_svc.EscalationError):
        esc_svc.relearn_concept(db, lesson, "n1")  # paused: continue or skip first
    esc_svc.skip_concept(db, lesson)
    node = esc_svc.relearn_concept(db, lesson, "n1")
    assert lesson.current_node_index == 1 and lesson.resume_point["return_index"] == 2
    node.status = "mastered"
    resolved = esc_svc.on_node_closed(db, lesson, node)
    assert node.review_note == "after review" and resolved.status == "resolved"
    assert esc_svc.finish_relearn(lesson)["return_index"] == 2 and lesson.resume_point is None


def test_practice_lists_wrong_first_and_never_changes_the_lesson(db):
    lesson = _lesson(db)
    right = Interaction(lesson_id=lesson.id, node_id="n0", question_text="Q right?", question_type="mcq",
                        options=["A", "B"], expected_concept="A", correct=True, raw_answer="A")
    wrong = Interaction(lesson_id=lesson.id, node_id="n0", question_text="Q wrong?", question_type="mcq",
                        options=["C", "D"], expected_concept="D", correct=False, raw_answer="C")
    pending = Interaction(lesson_id=lesson.id, node_id="n1", question_text="Q pending?",
                          question_type="mcq", options=["E"], expected_concept="E")
    db.add_all([right, wrong, pending])
    db.flush()
    before = (lesson.status, [(n.status, n.mastery_score) for n in lesson.nodes], wrong.correct)

    items = practice_service.practice_set(db, lesson, lesson.user_id)
    assert [i["question_text"] for i in items] == ["Q wrong?", "Q right?"]  # ungraded excluded
    assert "expected_concept" not in items[0]

    result = practice_service.grade(db, lesson, lesson.user_id, wrong.id, "D")
    assert result["correct"] is True
    assert practice_service.grade(db, lesson, lesson.user_id, wrong.id, "C")["correct"] is False
    assert (lesson.status, [(n.status, n.mastery_score) for n in lesson.nodes], wrong.correct) == before
    assert practice_service.practice_set(db, lesson, lesson.user_id)[0]["last_practice"]["correct"] is False

    with pytest.raises(practice_service.PracticeError):
        practice_service.grade(db, lesson, lesson.user_id, pending.id, "E")  # still on screen
