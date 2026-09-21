"""The cross-lesson memory payload handed to the planner.

Narrow by design: planning bias only, no transcripts, no identifiers.
"""
from modules.backend.src.db.models import LearnerProfileRow, Lesson, User
from modules.backend.src.services.session_manager import session_manager


def _lesson(db, **profile_fields) -> Lesson:
    user = User(
        email="memory@example.com",
        full_name="Memory Learner",
        password_hash="x",
        is_verified=True,
    )
    db.add(user)
    db.flush()

    if profile_fields:
        db.add(LearnerProfileRow(user_id=user.id, **profile_fields))

    lesson = Lesson(user_id=user.id, title="Newton's Laws", topic="Newton's Laws")
    db.add(lesson)
    db.flush()
    return lesson


def test_a_learner_with_no_profile_has_no_memory(db):
    lesson = _lesson(db)
    assert session_manager.memory_for(lesson, db) is None


def test_an_empty_profile_counts_as_no_memory(db):
    """A profile row exists after signup; an untaught learner still plans clean."""
    lesson = _lesson(db, strong_concepts=[], weak_concepts=[], misconception_counts={})
    assert session_manager.memory_for(lesson, db) is None


def test_memory_carries_concepts_and_recurring_misconceptions(db):
    lesson = _lesson(
        db,
        strong_concepts=["Scalars and vectors"],
        weak_concepts=["Net force"],
        misconception_counts={"confuses_net_force": 3, "sign_error": 2},
        lessons_completed=2,
    )

    memory = session_manager.memory_for(lesson, db)

    assert memory["strong_concepts"] == ["Scalars and vectors"]
    assert memory["weak_concepts"] == ["Net force"]
    # Ordered by how often the learner hit it.
    assert memory["recurring_misconceptions"] == ["confuses_net_force", "sign_error"]
    assert memory["lessons_completed"] == 2


def test_a_one_off_misconception_is_not_treated_as_recurring(db):
    lesson = _lesson(db, weak_concepts=["Net force"], misconception_counts={"slipped_once": 1})

    memory = session_manager.memory_for(lesson, db)

    assert memory["recurring_misconceptions"] == []


def test_memory_never_carries_identifying_or_raw_learner_content(db):
    lesson = _lesson(
        db,
        strong_concepts=["A"],
        weak_concepts=["B"],
        misconception_counts={"tag": 2},
        lessons_completed=1,
    )

    memory = session_manager.memory_for(lesson, db)

    assert set(memory) == {
        "strong_concepts",
        "weak_concepts",
        "recurring_misconceptions",
        "lessons_completed",
    }


def test_memory_is_unavailable_without_a_session_rather_than_guessed(db):
    """Mid-lesson steps pass no db; they must get None, not stale data."""
    lesson = _lesson(db, weak_concepts=["Net force"], misconception_counts={"tag": 2})
    assert session_manager.memory_for(lesson, None) is None
