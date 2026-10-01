"""Admin / mentor portal: live classrooms, the escalation inbox, learning
insights, AI quality and system health. Read-only over learner data.

Access: users with role "admin" or "teacher" (mentors need the inbox), plus
anyone listed in ADMIN_EMAILS.
"""
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.backend.src.db.base import get_db
from modules.backend.src.db.models import (
    Escalation, Interaction, Lesson, LessonEvent, LessonNodeRow, PracticeAttempt, User,
)
from modules.backend.src.deps import get_current_user
from modules.backend.src.services import escalation_service, lesson_service

router = APIRouter(prefix="/admin", tags=["admin"])
STARTED_AT = time.time()


def require_admin(user: User = Depends(get_current_user)) -> User:
    allowed = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
    if user.role in ("admin", "teacher") or user.email.lower() in allowed:
        return user
    raise HTTPException(status_code=403, detail="This area is for admins.")


def require_system_admin(user: User = Depends(require_admin)) -> User:
    """AI quality and system health are for admins; teachers see the teaching views."""
    allowed = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}
    if user.role == "admin" or user.email.lower() in allowed:
        return user
    raise HTTPException(status_code=403, detail="This area is for admins.")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _pct(part: float, whole: float) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def _active_sessions():
    from modules.backend.src.api.ws import _ACTIVE

    return [s for s in list(_ACTIVE.values()) if not s.done.is_set()]


@router.get("/overview")
def overview(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db, scope="function"),
    days: int = Query(default=14, ge=7, le=60),
):
    """The class at a glance, told the way the problem is: who understood first
    time, who the AI rescued by explaining again, and who needed a human."""
    since_day = _now() - timedelta(days=1)
    learners = db.scalar(select(func.count()).select_from(User).where(User.role == "student")) or 0
    lessons = db.scalars(select(Lesson)).all()
    owner = {l.id: l.user_id for l in lessons}
    graded = db.scalars(select(Interaction).where(Interaction.correct.is_not(None))).all()
    escalations = db.scalars(select(Escalation)).all()
    reports = [r for r in (lesson.report for lesson in lessons) if r is not None]

    active_today = {
        lid for (lid,) in db.execute(
            select(LessonEvent.lesson_id).where(LessonEvent.occurred_at >= since_day)
        ).all()
    }
    active_users = {lesson.user_id for lesson in lessons if lesson.id in active_today}

    # Per concept (lesson, node): first answer right = understood first time;
    # a wrong answer followed later by a right one = rescued by re-explanation.
    by_node: dict = {}
    for q in sorted(graded, key=lambda q: _aware(q.answered_at or q.asked_at)):
        by_node.setdefault((q.lesson_id, q.node_id), []).append(q)
    first_time = 0
    rescued_at = []
    for answers in by_node.values():
        if answers[0].correct:
            first_time += 1
            continue
        fix = next((q for q in answers if q.correct), None)
        if fix is not None:
            rescued_at.append(_aware(fix.answered_at or fix.asked_at).date())
    concepts_checked = len(by_node)
    still_stuck = concepts_checked - first_time - len(rescued_at)

    day_of = lambda dt: _aware(dt).date() if dt else None
    daily = []
    today = _now().date()
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        day_q = [q for q in graded if day_of(q.answered_at or q.asked_at) == day]
        daily.append({
            "date": day.isoformat(),
            "right": sum(1 for q in day_q if q.correct),
            "wrong": sum(1 for q in day_q if not q.correct),
            "rescued": sum(1 for d in rescued_at if d == day),
            "escalations": sum(1 for e in escalations if day_of(e.opened_at) == day),
            "completed": sum(1 for l in lessons if day_of(l.completed_at) == day),
            "started": sum(1 for l in lessons if day_of(l.created_at) == day),
            "learners": len({owner.get(q.lesson_id) for q in day_q} - {None}),
            # kept for older clients
            "lessons": sum(1 for l in lessons if day_of(l.created_at) == day),
            "questions": len(day_q),
        })

    return {
        "learners": learners,
        "active_today": len(active_users),
        "lessons": len(lessons),
        "completed": sum(1 for l in lessons if l.status == "completed"),
        "live_now": len(_active_sessions()),
        "open_escalations": sum(1 for e in escalations if e.status == "open"),
        "escalations_total": len(escalations),
        "questions_answered": len(graded),
        "accuracy_pct": _pct(sum(1 for q in graded if q.correct), len(graded)),
        "avg_score_pct": round(sum(r.score_pct for r in reports) / len(reports), 1) if reports else 0.0,
        "funnel": {
            "concepts_checked": concepts_checked,
            "first_time": first_time,
            "rescued": len(rescued_at),
            "still_stuck": max(0, still_stuck),
            "needed_human": len({(e.lesson_id, e.node_id) for e in escalations}),
        },
        "daily": daily,
    }


@router.get("/live")
def live(_: User = Depends(require_admin), db: Session = Depends(get_db, scope="function")):
    rows = []
    for session in _active_sessions():
        lesson = db.get(Lesson, session.lesson_id)
        if lesson is None:
            continue
        node = escalation_service.current_node_row(db, lesson)
        user = db.get(User, lesson.user_id)
        summary = lesson_service.lesson_summary(db, lesson)
        rows.append({
            "lesson_id": lesson.id,
            "title": lesson.title,
            "learner": user.full_name if user else "",
            "concept": node.concept if node else None,
            "fsm_state": lesson.fsm_state,
            "progress_pct": summary["progress_pct"],
            "connected_for_sec": int(time.time() - getattr(session, "connected_at", time.time())),
        })
    return {"sessions": rows}


@router.get("/escalations")
def escalations(
    status: Optional[str] = Query(default=None),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db, scope="function"),
):
    query = select(Escalation).order_by(Escalation.opened_at.desc())
    if status and status != "all":
        query = query.where(Escalation.status == status)
    items = []
    for esc in db.scalars(query.limit(200)).all():
        lesson = db.get(Lesson, esc.lesson_id)
        user = db.get(User, esc.user_id)
        last = lesson_service.latest_interaction(db, lesson, esc.node_id) if lesson else None
        wrong = db.scalar(
            select(func.count()).select_from(Interaction).where(
                Interaction.lesson_id == esc.lesson_id, Interaction.node_id == esc.node_id,
                Interaction.correct.is_(False),
            )
        ) or 0
        end = _aware(esc.closed_at) or _now()
        items.append({
            **escalation_service.as_dict(esc),
            "learner": user.full_name if user else "",
            "learner_email": user.email if user else "",
            "lesson_title": lesson.title if lesson else "",
            "last_question": last.question_text if last else None,
            "last_answer": last.raw_answer if last else None,
            "wrong_answers": wrong,
            "minutes_open": int((end - _aware(esc.opened_at)).total_seconds() // 60),
        })
    counts = dict(
        db.execute(select(Escalation.status, func.count()).group_by(Escalation.status)).all()
    )
    return {"escalations": items, "counts": counts}


@router.get("/insights")
def insights(_: User = Depends(require_admin), db: Session = Depends(get_db, scope="function")):
    graded = db.scalars(select(Interaction).where(Interaction.correct.is_not(None))).all()
    nodes = {(n.lesson_id, n.node_id): n for n in db.scalars(select(LessonNodeRow)).all()}
    owner = {l.id: l.user_id for l in db.scalars(select(Lesson)).all()}

    by_concept: dict[str, dict] = defaultdict(lambda: {"attempts": 0, "right": 0, "learners": set()})
    by_question: dict[str, dict] = defaultdict(lambda: {"asked": 0, "wrong": 0, "concept": ""})
    for q in graded:
        node = nodes.get((q.lesson_id, q.node_id))
        concept = node.concept if node else q.node_id
        bucket = by_concept[concept.strip().lower()]
        bucket["concept"] = concept
        bucket["attempts"] += 1
        bucket["right"] += 1 if q.correct else 0
        bucket["learners"].add(owner.get(q.lesson_id))
        qb = by_question[q.question_text.strip()]
        qb["asked"] += 1
        qb["wrong"] += 0 if q.correct else 1
        qb["concept"] = concept

    hardest = sorted(
        ({"concept": b["concept"], "attempts": b["attempts"], "accuracy_pct": _pct(b["right"], b["attempts"]),
          "learners": len(b["learners"])} for b in by_concept.values()),
        key=lambda x: (x["accuracy_pct"], -x["attempts"]),
    )[:10]
    missed = sorted(
        ({"question": q, "concept": b["concept"], "asked": b["asked"], "wrong_pct": _pct(b["wrong"], b["asked"])}
         for q, b in by_question.items() if b["wrong"]),
        key=lambda x: (-x["wrong_pct"], -x["asked"]),
    )[:10]
    mastered = [n for n in nodes.values() if n.status == "mastered" and n.attempts > 0]
    return {
        "hardest_concepts": hardest,
        "missed_questions": missed,
        "misconceptions": [
            {"tag": tag, "count": n}
            for tag, n in Counter(q.misconception_tag for q in graded if q.misconception_tag).most_common(8)
        ],
        "attempts_to_mastery": round(sum(n.attempts for n in mastered) / len(mastered), 2) if mastered else 0.0,
        "adaptation_mix": dict(Counter(q.adaptation_action for q in graded if q.adaptation_action)),
    }


@router.get("/quality")
def quality(_: User = Depends(require_system_admin), db: Session = Depends(get_db, scope="function")):
    from modules.ai_agent_orchestration.src.adapters import gemini_adapter

    grounding = Counter(
        (n.citation_json or {}).get("risk_level", "no_document_context")
        for n in db.scalars(select(LessonNodeRow).where(LessonNodeRow.citation_json.is_not(None))).all()
    )
    segments = db.scalars(
        select(LessonEvent).where(LessonEvent.event_type == "agent.segment_generated")
    ).all()
    words = [int((e.payload or {}).get("script_words") or 0) for e in segments]
    remaining = max(0.0, gemini_adapter._cooldown["until"] - time.monotonic())
    questions = Counter(
        q.question_type for q in db.scalars(select(Interaction)).all()
    )
    return {
        "grounding": dict(grounding),
        "llm": {
            "live": bool(os.getenv("GEMINI_API_KEY", "").strip()),
            "model": os.getenv("GEMINI_MODEL", "gemini"),
            "cooldown_active": remaining > 0,
            "cooldown_remaining_sec": int(remaining),
        },
        "script_words_vs_target": round(sum(words) / len(words), 1) if words else None,
        "explanations": len(segments),
        "questions_by_type": dict(questions),
    }


@router.get("/pipeline")
def pipeline(_: User = Depends(require_system_admin), db: Session = Depends(get_db, scope="function")):
    rendered = db.scalars(select(LessonNodeRow).where(LessonNodeRow.video_url.is_not(None))).all()
    hour_ago = _now() - timedelta(hours=1)
    day_ago = _now() - timedelta(days=1)
    recent = Counter(
        e for (e,) in db.execute(select(LessonEvent.event_type).where(LessonEvent.occurred_at >= hour_ago)).all()
    )
    memory = None
    try:
        import resource
        import sys

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory = round(rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024, 1)
    except Exception:
        pass
    return {
        "renders": {
            "total": len(rendered),
            "avg_video_sec": round(sum(n.duration_sec for n in rendered) / len(rendered), 1) if rendered else 0.0,
            "failed": db.scalar(
                select(func.count()).select_from(LessonEvent).where(LessonEvent.event_type == "render_failed")
            ) or 0,
        },
        "memory_mb": memory,
        "uptime_sec": int(time.time() - STARTED_AT),
        "events_last_hour": dict(recent.most_common(12)),
        "reconnects_today": db.scalar(
            select(func.count()).select_from(LessonEvent).where(
                LessonEvent.event_type == "disconnected", LessonEvent.occurred_at >= day_ago
            )
        ) or 0,
    }


def _learner_row(db: Session, user: User) -> dict:
    lessons = db.scalars(select(Lesson).where(Lesson.user_id == user.id)).all()
    ids = [l.id for l in lessons]
    graded = db.scalars(
        select(Interaction).where(Interaction.lesson_id.in_(ids), Interaction.correct.is_not(None))
    ).all() if ids else []
    last = max((_aware(l.updated_at) for l in lessons), default=None)
    out = _identity(user)
    return {
        **out,
        "lessons": len(lessons),
        "completed": sum(1 for l in lessons if l.status == "completed"),
        "accuracy_pct": _pct(sum(1 for q in graded if q.correct), len(graded)),
        "last_active": last.isoformat() if last else None,
        "open_escalations": db.scalar(
            select(func.count()).select_from(Escalation).where(
                Escalation.user_id == user.id, Escalation.status == "open"
            )
        ) or 0,
    }


def _identity(user: User) -> dict:
    from modules.backend.src.api.auth_routes import _user_out

    data = _user_out(user)
    return {
        "id": data.id, "full_name": data.full_name, "email": data.email,
        "avatar_color": data.avatar_color, "avatar_url": data.avatar_url,
    }


@router.get("/learners")
def learners(
    q: str = Query(default="", max_length=120),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db, scope="function"),
):
    query = select(User).order_by(User.created_at.desc())
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.where((User.full_name.ilike(like)) | (User.email.ilike(like)))
    return {"learners": [_learner_row(db, u) for u in db.scalars(query.limit(100)).all()]}


@router.get("/learners/{user_id}")
def learner(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db, scope="function")):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Learner not found.")
    lessons = db.scalars(select(Lesson).where(Lesson.user_id == user.id).order_by(Lesson.updated_at.desc())).all()
    profile = lesson_service.refresh_learner_profile(db, user.id)
    return {
        "learner": {**_learner_row(db, user), "grade": user.grade, "created_at": user.created_at.isoformat()},
        "lessons": [lesson_service.lesson_summary(db, l) for l in lessons],
        "strong_concepts": profile.strong_concepts[:12],
        "weak_concepts": profile.weak_concepts[:12],
        "escalations": [
            escalation_service.as_dict(e)
            for e in db.scalars(select(Escalation).where(Escalation.user_id == user.id)
                                .order_by(Escalation.opened_at.desc())).all()
        ],
        "practice_attempts": db.scalar(
            select(func.count()).select_from(PracticeAttempt).where(PracticeAttempt.user_id == user.id)
        ) or 0,
    }

