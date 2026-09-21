"""Persistence and aggregation for lessons, per-node progress, and learner mastery."""
import logging
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.backend.src.config import settings
from modules.backend.src.db.models import (
    Interaction,
    LearnerProfileRow,
    Lesson,
    LessonEvent,
    LessonNodeRow,
    ReportRow,
    User,
    utcnow,
)

logger = logging.getLogger(__name__)

MASTERY_THRESHOLD = 0.6


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _as_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(obj)


# --------------------------------------------------------------------------
# Plan persistence
# --------------------------------------------------------------------------

def persist_plan(db: Session, lesson: Lesson, plan: Any) -> Lesson:
    """Write an orchestrator LessonPlan into lessons + lesson_nodes."""
    plan_dict = _as_dict(plan)
    lesson.plan_json = plan_dict
    lesson.plan_lesson_id = plan_dict.get("lesson_id")
    lesson.status = "planned"
    lesson.fsm_state = "PLANNED"

    nodes = plan_dict.get("nodes") or []

    # Re-planning replaces nodes the learner has not reached yet, and keeps
    # progress on the ones already taught.
    existing = {n.node_id: n for n in lesson.nodes}
    keep_ids = set()

    for position, raw in enumerate(nodes):
        node_id = raw.get("node_id") or f"node-{position + 1}"
        keep_ids.add(node_id)
        row = existing.get(node_id)
        if row is None:
            row = LessonNodeRow(lesson_id=lesson.id, node_id=node_id, position=position)
            db.add(row)
        row.position = position
        row.concept = raw.get("concept", "Untitled concept")
        row.depth = raw.get("depth", "core")
        row.est_minutes = int(raw.get("est_minutes") or 3)
        row.visual_type = raw.get("visual_type", "diagram")
        row.checkpoint_question = bool(raw.get("checkpoint_question"))

    for node_id, row in existing.items():
        if node_id not in keep_ids and row.status == "pending":
            db.delete(row)

    if not lesson.title or lesson.title == "Untitled lesson":
        lesson.title = _derive_title(lesson, nodes)

    db.flush()
    log_event(db, lesson, "plan_generated", payload={"node_count": len(nodes)})
    return lesson


def _derive_title(lesson: Lesson, nodes: list) -> str:
    if lesson.topic:
        return lesson.topic[:280]
    if nodes:
        first = nodes[0].get("concept", "")
        return first.split(":")[0][:280] or "Lesson"
    return "Lesson"


# --------------------------------------------------------------------------
# Live progress writes
# --------------------------------------------------------------------------

def get_node(db: Session, lesson: Lesson, node_id: str) -> Optional[LessonNodeRow]:
    return db.scalars(
        select(LessonNodeRow).where(
            LessonNodeRow.lesson_id == lesson.id, LessonNodeRow.node_id == node_id
        )
    ).first()


def mark_node_teaching(db: Session, lesson: Lesson, node_id: str, script_text: str) -> None:
    node = get_node(db, lesson, node_id)
    if not node:
        return
    if node.first_seen_at is None:
        node.first_seen_at = utcnow()
    else:
        node.times_reexplained += 1
    node.status = "teaching"
    node.script_text = script_text
    if lesson.status in ("created", "planned"):
        lesson.status = "in_progress"
        lesson.started_at = lesson.started_at or utcnow()
    lesson.fsm_state = "EXPLAIN"
    db.flush()


def attach_media(
    db: Session,
    lesson: Lesson,
    node_id: str,
    video_path: str,
    duration_sec: float,
    captions_path: Optional[str] = None,
) -> Optional[str]:
    """Copy a rendered segment into the media root and record its served URL.

    Renders land in a temp directory that the OS may clear, so lessons would
    lose their video on rewatch. Copying under data/media makes history durable.
    """
    node = get_node(db, lesson, node_id)
    if not node:
        return None

    stored_url = None
    try:
        source = Path(video_path)
        if source.exists():
            dest_dir = settings.media_root / lesson.id
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{node_id}_{source.name}"
            if not dest.exists():
                shutil.copy2(source, dest)
            node.video_path = str(dest)
            stored_url = f"{settings.api_v1_str}/lessons/{lesson.id}/nodes/{node_id}/video"
        else:
            logger.warning("Rendered video missing at %s", video_path)
    except OSError as exc:
        logger.error("Could not persist video for %s/%s: %s", lesson.id, node_id, exc)

    if captions_path:
        try:
            csource = Path(captions_path)
            if csource.exists():
                dest_dir = settings.media_root / lesson.id
                dest_dir.mkdir(parents=True, exist_ok=True)
                cdest = dest_dir / f"{node_id}_{csource.name}"
                if not cdest.exists():
                    shutil.copy2(csource, cdest)
                node.captions_url = (
                    f"{settings.api_v1_str}/lessons/{lesson.id}/nodes/{node_id}/captions"
                )
        except OSError:
            pass

    node.video_url = stored_url
    node.duration_sec = float(duration_sec or 0.0)
    lesson.total_watch_sec = (lesson.total_watch_sec or 0.0) + float(duration_sec or 0.0)
    db.flush()
    return stored_url


def record_notes(db: Session, lesson: Lesson, node_id: str, notes: dict) -> None:
    """Persist the Explainer's chapter notes so they outlive the live socket."""
    node = get_node(db, lesson, node_id)
    if not node or not notes:
        return
    node.notes_json = notes
    db.flush()


def lesson_notes_markdown(db: Session, lesson: Lesson) -> str:
    """The whole lesson as a Markdown study sheet, ready to download."""
    nodes = sorted(lesson.nodes, key=lambda n: n.position)
    taught = [n for n in nodes if n.script_text or n.notes_json]

    lines = [f"# {lesson.title}", ""]
    when = (lesson.started_at or lesson.created_at)
    if when:
        lines += [f"_Lesson notes · {when.strftime('%d %b %Y')}_", ""]

    for node in taught:
        lines += [f"## {node.concept}", ""]
        meta = [node.depth, f"{node.est_minutes} min"]
        if node.status:
            meta.append(node.status)
        lines += ["*" + " · ".join(str(m) for m in meta if m) + "*", ""]

        notes = node.notes_json or {}
        points = [p for p in (notes.get("key_points") or []) if p]
        if not points and node.script_text:
            points = [s.strip() for s in node.script_text.split(". ")[:4] if s.strip()]
        for point in points:
            lines.append(f"- {point.rstrip('.')}.")
        lines.append("")

        if notes.get("example"):
            lines += ["**Example.** " + str(notes["example"]), ""]

        citation = node.citation_json or {}
        if citation.get("excerpt"):
            lines += [f"> From your material: {citation['excerpt']}", ""]

        if node.script_text:
            lines += ["<details><summary>Full transcript</summary>", "",
                      node.script_text, "", "</details>", ""]

    takeaways = []
    for node in taught:
        points = ((node.notes_json or {}).get("key_points") or [])[:1]
        takeaways += [f"- **{node.concept}** — {p}" for p in points]
    if takeaways:
        lines += ["## Key takeaways", ""] + takeaways + [""]

    if not taught:
        lines += ["_No concepts have been taught in this lesson yet._", ""]

    return "\n".join(lines)


def record_citation(db: Session, lesson: Lesson, node_id: str, citation: dict) -> None:
    node = get_node(db, lesson, node_id)
    if node:
        node.citation_json = citation
        db.flush()


def record_question(db: Session, lesson: Lesson, question: Any) -> Interaction:
    q = _as_dict(question)
    node_id = q.get("node_id", "")
    node = get_node(db, lesson, node_id)
    if node:
        node.status = "questioning"
        node.attempts += 1

    interaction = Interaction(
        lesson_id=lesson.id,
        node_id=node_id,
        question_text=q.get("question_text", ""),
        question_type=q.get("type", "short_answer"),
        options=q.get("options") or [],
        expected_concept=q.get("expected_concept", "") or "",
    )
    db.add(interaction)
    lesson.fsm_state = "QUESTION"
    db.flush()
    return interaction


def record_answer(
    db: Session,
    interaction: Interaction,
    raw_answer: str,
    response_time_sec: float,
) -> None:
    interaction.raw_answer = raw_answer
    interaction.response_time_sec = float(response_time_sec or 0.0)
    interaction.answered_at = utcnow()
    db.flush()


def record_evaluation(
    db: Session, lesson: Lesson, interaction: Interaction, evaluation: Any
) -> None:
    ev = _as_dict(evaluation)
    interaction.correct = bool(ev.get("correct"))
    interaction.partial_credit = float(ev.get("partial_credit") or 0.0)
    interaction.confidence = float(ev.get("confidence") or 0.0)
    interaction.misconception_tag = ev.get("misconception_tag")
    interaction.feedback_text = ev.get("feedback_text")

    node = get_node(db, lesson, interaction.node_id)
    if node:
        score = 1.0 if interaction.correct else float(interaction.partial_credit)
        node.mastery_score = max(node.mastery_score, score)
        node.status = "mastered" if score >= MASTERY_THRESHOLD else "struggling"
        if node.status == "mastered":
            node.completed_at = utcnow()
    lesson.fsm_state = "EVALUATE"
    db.flush()


def record_adaptation(db: Session, lesson: Lesson, interaction: Interaction, decision: Any) -> None:
    d = _as_dict(decision)
    interaction.adaptation_action = d.get("action")
    interaction.adaptation_reason = d.get("reason")
    lesson.fsm_state = "ADAPT"
    db.flush()


def agent_trace(db: Session, lesson: Lesson, limit: int = 500) -> list[dict]:
    """The lesson's agent-decision trace, oldest first.

    Only `agent.*` events are returned: lifecycle rows (lesson_created,
    disconnected, mentor_notified) share the table but are not agent decisions.
    """
    rows = db.scalars(
        select(LessonEvent)
        .where(
            LessonEvent.lesson_id == lesson.id,
            LessonEvent.event_type.like("agent.%"),
        )
        .order_by(LessonEvent.occurred_at.asc(), LessonEvent.id.asc())
        .limit(limit)
    ).all()
    return [
        {
            "event_type": row.event_type,
            "node_id": row.node_id,
            "occurred_at": row.occurred_at.isoformat(),
            "payload": row.payload or {},
        }
        for row in rows
    ]


def latest_interaction(db: Session, lesson: Lesson, node_id: str) -> Optional[Interaction]:
    """Most recent question/answer for a node — the one that triggered escalation."""
    return db.scalars(
        select(Interaction)
        .where(Interaction.lesson_id == lesson.id, Interaction.node_id == node_id)
        .order_by(Interaction.asked_at.desc())
    ).first()


def failure_count(db: Session, lesson: Lesson, node_id: str) -> int:
    """How many consecutive wrong/partial attempts led to this escalation."""
    return db.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.lesson_id == lesson.id,
            Interaction.node_id == node_id,
            Interaction.correct.is_(False),
        )
    ) or 0


def already_notified_mentor(db: Session, lesson: Lesson, node_id: str) -> bool:
    """Idempotency check: one mentor email per node per lesson, not per retry/reconnect."""
    return db.scalars(
        select(LessonEvent).where(
            LessonEvent.lesson_id == lesson.id,
            LessonEvent.event_type == "mentor_notified",
            LessonEvent.node_id == node_id,
        )
    ).first() is not None


def advance_node(db: Session, lesson: Lesson, node_index: int) -> None:
    lesson.current_node_index = node_index
    lesson.fsm_state = "CONTINUE"
    db.flush()


def log_event(
    db: Session,
    lesson: Lesson,
    event_type: str,
    node_id: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    db.add(
        LessonEvent(
            lesson_id=lesson.id, event_type=event_type, node_id=node_id, payload=payload or {}
        )
    )
    db.flush()


# --------------------------------------------------------------------------
# Completion & profile rollup
# --------------------------------------------------------------------------

def complete_lesson(db: Session, lesson: Lesson, report: Any) -> ReportRow:
    r = _as_dict(report)

    # Prefer measured results over whatever the LLM narrates.
    measured = compute_lesson_score(db, lesson)
    score = measured if measured is not None else float(r.get("score_pct") or 0.0)

    row = db.scalars(select(ReportRow).where(ReportRow.lesson_id == lesson.id)).first()
    if row is None:
        row = ReportRow(lesson_id=lesson.id, user_id=lesson.user_id)
        db.add(row)

    strong, weak = _strong_weak_from_nodes(lesson)
    row.score_pct = round(score, 1)
    row.strong_areas = r.get("strong_areas") or strong
    row.weak_areas = r.get("weak_areas") or weak
    row.recommended_next = r.get("recommended_next") or []
    row.narrative_feedback = r.get("narrative_feedback") or ""

    lesson.status = "completed"
    lesson.fsm_state = "DONE"
    lesson.completed_at = utcnow()
    for node in lesson.nodes:
        if node.status in ("pending", "teaching", "questioning"):
            node.status = "mastered" if node.mastery_score >= MASTERY_THRESHOLD else "skipped"
    db.flush()

    refresh_learner_profile(db, lesson.user_id)
    log_event(db, lesson, "lesson_completed", payload={"score_pct": row.score_pct})
    return row


def compute_lesson_score(db: Session, lesson: Lesson) -> Optional[float]:
    """Score from the learner's best attempt per checkpoint, not raw attempt count."""
    interactions = db.scalars(
        select(Interaction).where(
            Interaction.lesson_id == lesson.id, Interaction.correct.isnot(None)
        )
    ).all()
    if not interactions:
        return None

    best: dict[str, float] = {}
    for item in interactions:
        score = 1.0 if item.correct else float(item.partial_credit or 0.0)
        best[item.node_id] = max(best.get(item.node_id, 0.0), score)
    return round(100.0 * sum(best.values()) / len(best), 1)


def _strong_weak_from_nodes(lesson: Lesson) -> tuple[list[str], list[str]]:
    strong = [n.concept for n in lesson.nodes if n.mastery_score >= 0.8]
    weak = [
        n.concept
        for n in lesson.nodes
        if n.attempts > 0 and n.mastery_score < MASTERY_THRESHOLD
    ]
    return strong[:8], weak[:8]


def refresh_learner_profile(db: Session, user_id: str) -> LearnerProfileRow:
    """Recompute the rolling mastery picture from all of a learner's lessons."""
    profile = db.get(LearnerProfileRow, user_id)
    if profile is None:
        profile = LearnerProfileRow(user_id=user_id)
        db.add(profile)
        db.flush()

    lessons = db.scalars(select(Lesson).where(Lesson.user_id == user_id)).all()
    lesson_ids = [lesson.id for lesson in lessons]

    profile.lessons_started = sum(1 for lesson in lessons if lesson.status != "created")
    profile.lessons_completed = sum(1 for lesson in lessons if lesson.status == "completed")
    profile.total_learning_sec = float(sum(lesson.total_watch_sec or 0.0 for lesson in lessons))

    if lesson_ids:
        interactions = db.scalars(
            select(Interaction).where(
                Interaction.lesson_id.in_(lesson_ids), Interaction.correct.isnot(None)
            )
        ).all()
        nodes = db.scalars(
            select(LessonNodeRow).where(LessonNodeRow.lesson_id.in_(lesson_ids))
        ).all()
    else:
        interactions, nodes = [], []

    profile.total_questions = len(interactions)
    profile.correct_questions = sum(1 for item in interactions if item.correct)

    counts: dict[str, int] = {}
    for item in interactions:
        if item.misconception_tag:
            counts[item.misconception_tag] = counts.get(item.misconception_tag, 0) + 1
    profile.misconception_counts = counts

    # Aggregate mastery per concept across every lesson that touched it.
    per_concept: dict[str, list[float]] = {}
    for node in nodes:
        if node.attempts == 0 and node.status == "pending":
            continue
        per_concept.setdefault(node.concept, []).append(node.mastery_score)

    strong, weak = [], []
    for concept, scores in per_concept.items():
        avg = sum(scores) / len(scores)
        (strong if avg >= 0.8 else weak if avg < MASTERY_THRESHOLD else []).append(concept)

    profile.strong_concepts = sorted(strong)[:40]
    profile.weak_concepts = sorted(weak)[:40]
    profile.current_learning_path = [
        node.concept
        for node in nodes
        if node.status in ("pending", "struggling")
    ][:12]

    _update_streak(profile, lessons)
    db.flush()
    return profile


def _update_streak(profile: LearnerProfileRow, lessons: list[Lesson]) -> None:
    """Count consecutive calendar days with activity, ending today or yesterday."""
    active_days = set()
    for lesson in lessons:
        for stamp in (lesson.started_at, lesson.completed_at, lesson.updated_at):
            if stamp:
                active_days.add(_aware(stamp).date())

    if not active_days:
        profile.streak_days = 0
        profile.last_active_date = None
        return

    today = datetime.now(timezone.utc).date()
    latest = max(active_days)
    profile.last_active_date = latest.isoformat()

    # A streak stays alive if the learner studied today or yesterday.
    if (today - latest).days > 1:
        profile.streak_days = 0
        profile.longest_streak = max(profile.longest_streak, _longest_run(active_days))
        return

    streak, cursor = 0, latest
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    profile.streak_days = streak
    profile.longest_streak = max(profile.longest_streak, streak, _longest_run(active_days))


def _longest_run(days: set[date]) -> int:
    if not days:
        return 0
    ordered = sorted(days)
    longest = run = 1
    for prev, curr in zip(ordered, ordered[1:]):
        run = run + 1 if (curr - prev).days == 1 else 1
        longest = max(longest, run)
    return longest


# --------------------------------------------------------------------------
# Dashboard aggregation
# --------------------------------------------------------------------------

def dashboard_summary(db: Session, user: User) -> dict:
    profile = db.get(LearnerProfileRow, user.id) or refresh_learner_profile(db, user.id)

    lessons = db.scalars(
        select(Lesson).where(Lesson.user_id == user.id).order_by(Lesson.updated_at.desc())
    ).all()

    completed = [lesson for lesson in lessons if lesson.status == "completed"]
    in_progress = [lesson for lesson in lessons if lesson.status == "in_progress"]

    reports = db.scalars(
        select(ReportRow).where(ReportRow.user_id == user.id).order_by(ReportRow.created_at.desc())
    ).all()
    avg_score = round(sum(r.score_pct for r in reports) / len(reports), 1) if reports else 0.0

    accuracy = (
        round(100.0 * profile.correct_questions / profile.total_questions, 1)
        if profile.total_questions
        else 0.0
    )

    resume = in_progress[0] if in_progress else None

    return {
        "learner": {
            "id": user.id,
            "full_name": user.full_name,
            "initials": user.initials,
            "email": user.email,
            "grade": user.grade,
            "board": user.board,
            "avatar_color": user.avatar_color,
            "member_since": user.created_at.isoformat(),
        },
        "stats": {
            "lessons_started": profile.lessons_started,
            "lessons_completed": profile.lessons_completed,
            "lessons_in_progress": len(in_progress),
            "average_score_pct": avg_score,
            "accuracy_pct": accuracy,
            "total_questions": profile.total_questions,
            "correct_questions": profile.correct_questions,
            "learning_minutes": round(profile.total_learning_sec / 60.0, 1),
            "streak_days": profile.streak_days,
            "longest_streak": profile.longest_streak,
            "concepts_mastered": len(profile.strong_concepts),
            "concepts_to_review": len(profile.weak_concepts),
        },
        "strong_concepts": profile.strong_concepts[:10],
        "weak_concepts": profile.weak_concepts[:10],
        "misconceptions": sorted(
            ({"tag": k, "count": v} for k, v in (profile.misconception_counts or {}).items()),
            key=lambda x: -x["count"],
        )[:6],
        "resume_lesson": lesson_summary(db, resume) if resume else None,
        "recent_lessons": [lesson_summary(db, lesson) for lesson in lessons[:6]],
        "score_trend": [
            {
                "lesson_id": r.lesson_id,
                "score_pct": r.score_pct,
                "date": r.created_at.isoformat(),
            }
            for r in list(reversed(reports))[-12:]
        ],
        "activity_calendar": _activity_calendar(lessons),
    }


def _activity_calendar(lessons: list[Lesson]) -> list[dict]:
    """Last 84 days of per-day lesson activity, for the dashboard heat strip."""
    counts: dict[str, int] = {}
    for lesson in lessons:
        stamp = lesson.completed_at or lesson.started_at or lesson.created_at
        if stamp:
            key = _aware(stamp).date().isoformat()
            counts[key] = counts.get(key, 0) + 1

    today = datetime.now(timezone.utc).date()
    return [
        {
            "date": (day := (today - timedelta(days=offset))).isoformat(),
            "count": counts.get(day.isoformat(), 0),
        }
        for offset in range(83, -1, -1)
    ]


def lesson_summary(db: Session, lesson: Optional[Lesson]) -> Optional[dict]:
    if lesson is None:
        return None
    total = len(lesson.nodes)
    done = sum(1 for n in lesson.nodes if n.status in ("mastered", "skipped"))
    report = db.scalars(select(ReportRow).where(ReportRow.lesson_id == lesson.id)).first()

    return {
        "id": lesson.id,
        "title": lesson.title,
        "source": lesson.source,
        "topic": lesson.topic,
        "status": lesson.status,
        "level": lesson.level,
        "language": lesson.language,
        "node_count": total,
        "nodes_completed": done,
        "progress_pct": round(100.0 * done / total, 1) if total else 0.0,
        "score_pct": report.score_pct if report else None,
        "watch_minutes": round((lesson.total_watch_sec or 0) / 60.0, 1),
        "created_at": lesson.created_at.isoformat(),
        "updated_at": lesson.updated_at.isoformat(),
        "completed_at": lesson.completed_at.isoformat() if lesson.completed_at else None,
    }


def lesson_detail(db: Session, lesson: Lesson) -> dict:
    summary = lesson_summary(db, lesson)
    report = db.scalars(select(ReportRow).where(ReportRow.lesson_id == lesson.id)).first()
    interactions = db.scalars(
        select(Interaction)
        .where(Interaction.lesson_id == lesson.id)
        .order_by(Interaction.asked_at.asc())
    ).all()

    by_node: dict[str, list[dict]] = {}
    for item in interactions:
        by_node.setdefault(item.node_id, []).append(
            {
                "id": item.id,
                "question_text": item.question_text,
                "question_type": item.question_type,
                "options": item.options,
                "expected_concept": item.expected_concept,
                "raw_answer": item.raw_answer,
                "correct": item.correct,
                "partial_credit": item.partial_credit,
                "confidence": item.confidence,
                "misconception_tag": item.misconception_tag,
                "feedback_text": item.feedback_text,
                "adaptation_action": item.adaptation_action,
                "adaptation_reason": item.adaptation_reason,
                "response_time_sec": item.response_time_sec,
                "asked_at": item.asked_at.isoformat(),
            }
        )

    summary["nodes"] = [
        {
            "node_id": n.node_id,
            "position": n.position,
            "concept": n.concept,
            "depth": n.depth,
            "est_minutes": n.est_minutes,
            "visual_type": n.visual_type,
            "checkpoint_question": n.checkpoint_question,
            "status": n.status,
            "attempts": n.attempts,
            "mastery_score": round(n.mastery_score, 2),
            "times_reexplained": n.times_reexplained,
            "script_text": n.script_text,
            "notes": n.notes_json,
            "video_url": n.video_url,
            "captions_url": n.captions_url,
            "duration_sec": n.duration_sec,
            "citation": n.citation_json,
            "interactions": by_node.get(n.node_id, []),
        }
        for n in sorted(lesson.nodes, key=lambda x: x.position)
    ]
    summary["report"] = (
        {
            "score_pct": report.score_pct,
            "strong_areas": report.strong_areas,
            "weak_areas": report.weak_areas,
            "recommended_next": report.recommended_next,
            "narrative_feedback": report.narrative_feedback,
            "created_at": report.created_at.isoformat(),
        }
        if report
        else None
    )
    summary["constraints"] = {
        "level": lesson.level,
        "language": lesson.language,
        "time_budget_min": lesson.time_budget_min,
        "style": lesson.style,
    }
    return summary


def analytics(db: Session, user: User) -> dict:
    """Time-series and distribution data for the progress analytics page."""
    profile = db.get(LearnerProfileRow, user.id) or refresh_learner_profile(db, user.id)
    lessons = db.scalars(
        select(Lesson).where(Lesson.user_id == user.id).order_by(Lesson.created_at.asc())
    ).all()
    lesson_ids = [lesson.id for lesson in lessons]

    interactions = (
        db.scalars(
            select(Interaction)
            .where(Interaction.lesson_id.in_(lesson_ids), Interaction.correct.isnot(None))
            .order_by(Interaction.asked_at.asc())
        ).all()
        if lesson_ids
        else []
    )
    nodes = (
        db.scalars(select(LessonNodeRow).where(LessonNodeRow.lesson_id.in_(lesson_ids))).all()
        if lesson_ids
        else []
    )

    # Accuracy per day
    per_day: dict[str, dict[str, int]] = {}
    for item in interactions:
        key = _aware(item.asked_at).date().isoformat()
        bucket = per_day.setdefault(key, {"total": 0, "correct": 0})
        bucket["total"] += 1
        bucket["correct"] += 1 if item.correct else 0

    accuracy_trend = [
        {
            "date": day,
            "accuracy_pct": round(100.0 * v["correct"] / v["total"], 1),
            "questions": v["total"],
        }
        for day, v in sorted(per_day.items())
    ]

    concept_map = {}
    for node in nodes:
        if node.attempts == 0 and node.status == "pending":
            continue
        entry = concept_map.setdefault(
            node.concept, {"concept": node.concept, "scores": [], "attempts": 0, "reexplains": 0}
        )
        entry["scores"].append(node.mastery_score)
        entry["attempts"] += node.attempts
        entry["reexplains"] += node.times_reexplained

    concept_strength = sorted(
        (
            {
                "concept": v["concept"],
                "mastery_pct": round(100.0 * sum(v["scores"]) / len(v["scores"]), 1),
                "attempts": v["attempts"],
                "reexplains": v["reexplains"],
            }
            for v in concept_map.values()
        ),
        key=lambda x: x["mastery_pct"],
    )

    minutes_per_day: dict[str, float] = {}
    for lesson in lessons:
        stamp = lesson.completed_at or lesson.started_at or lesson.created_at
        key = _aware(stamp).date().isoformat()
        minutes_per_day[key] = minutes_per_day.get(key, 0.0) + (lesson.total_watch_sec or 0) / 60.0

    return {
        "accuracy_trend": accuracy_trend,
        "concept_strength": concept_strength,
        "weakest": concept_strength[:6],
        "strongest": list(reversed(concept_strength))[:6],
        "misconceptions": sorted(
            ({"tag": k, "count": v} for k, v in (profile.misconception_counts or {}).items()),
            key=lambda x: -x["count"],
        ),
        "time_on_task": [
            {"date": d, "minutes": round(m, 1)} for d, m in sorted(minutes_per_day.items())
        ],
        "response_time": {
            "average_sec": round(
                sum(i.response_time_sec for i in interactions) / len(interactions), 1
            )
            if interactions
            else 0.0,
            "samples": len(interactions),
        },
        "by_level": _group_count(db, user.id, Lesson.level),
        "by_language": _group_count(db, user.id, Lesson.language),
        "totals": {
            "lessons": len(lessons),
            "completed": sum(1 for lesson in lessons if lesson.status == "completed"),
            "questions": len(interactions),
            "correct": sum(1 for i in interactions if i.correct),
            "learning_minutes": round(profile.total_learning_sec / 60.0, 1),
        },
    }


def _group_count(db: Session, user_id: str, column) -> list[dict]:
    rows = db.execute(
        select(column, func.count()).where(Lesson.user_id == user_id).group_by(column)
    ).all()
    return [{"key": key, "count": count} for key, count in rows]
