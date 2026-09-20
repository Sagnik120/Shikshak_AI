"""Dashboard, learner profile, and progress analytics — all computed from SQLite."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from modules.backend.src.db.base import get_db
from modules.backend.src.db.models import User
from modules.backend.src.deps import get_current_user
from modules.backend.src.services import lesson_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return lesson_service.dashboard_summary(db, user)


@router.get("/analytics")
def analytics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return lesson_service.analytics(db, user)


@router.get("/profile/learning")
def learner_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The rolling mastery profile that drives adaptive planning."""
    profile = lesson_service.refresh_learner_profile(db, user.id)
    return {
        "learner_id": user.id,
        "strong_concepts": profile.strong_concepts,
        "weak_concepts": profile.weak_concepts,
        "current_learning_path": profile.current_learning_path,
        "misconception_counts": profile.misconception_counts,
        "preferred_language": user.preferred_language,
        "preferred_level": user.preferred_level,
        "lessons_started": profile.lessons_started,
        "lessons_completed": profile.lessons_completed,
        "streak_days": profile.streak_days,
        "longest_streak": profile.longest_streak,
        "total_learning_minutes": round(profile.total_learning_sec / 60.0, 1),
    }
