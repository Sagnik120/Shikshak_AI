"""A learner's journey: real day-by-day activity, streaks, XP/levels, mastery
and achievement badges — all derived from what the learner actually did
(answers, videos watched, practice, lessons), never from self-reports.

One read-only pass over the learner's rows; nothing here writes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.backend.src.db.models import (
    Document,
    Interaction,
    Lesson,
    LessonNodeRow,
    PracticeAttempt,
    ReportRow,
    User,
)

MAX_DAYS = 730
MONTH_BADGE_DAYS = 20  # active on this many days in a calendar month earns that month's badge
MASTERED = {"mastered"}
DONE = {"mastered", "completed"}

# Badge groups: thresholds in tier order (bronze → silver → gold → platinum → diamond …).
BADGES: dict[str, list[int]] = {
    "first_lesson": [1],
    "lessons_completed": [1, 5, 10, 25, 50, 100],
    "streak": [3, 7, 14, 30, 50, 100, 365, 500],
    "active_days": [10, 50, 100, 365],
    "answers": [10, 100, 500, 1000],
    "right_in_a_row": [5, 10, 25],
    "concepts_mastered": [10, 50, 100],
    "perfect_lesson": [1, 5],
    "comeback": [1, 5],
    "own_notes": [1, 5],
    "practice": [10, 50],
    "bilingual": [1],
}

LEVEL_TITLES = [(1, "curious"), (2, "explorer"), (4, "scholar"), (7, "thinker"), (10, "guru")]


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _day(dt: Optional[datetime]) -> Optional[date]:
    a = _aware(dt)
    return a.date() if a else None


def _nth(stamps: Iterable[Optional[datetime]], n: int) -> Optional[str]:
    """When the n-th event happened (ISO date), or None if it hasn't yet."""
    ordered = sorted(s for s in (_aware(x) for x in stamps) if s)
    return ordered[n - 1].date().isoformat() if len(ordered) >= n else None


def _runs(days: set[date]) -> tuple[int, int, dict[int, str]]:
    """Current streak (ending today/yesterday), longest streak, and the date a
    run first reached each length."""
    if not days:
        return 0, 0, {}
    ordered = sorted(days)
    reached: dict[int, str] = {}
    longest = run = 0
    prev: Optional[date] = None
    for d in ordered:
        run = run + 1 if prev and (d - prev).days == 1 else 1
        longest = max(longest, run)
        reached.setdefault(run, d.isoformat())
        prev = d
    today = datetime.now(timezone.utc).date()
    current = 0
    latest = ordered[-1]
    if (today - latest).days <= 1:
        cursor = latest
        while cursor in days:
            current += 1
            cursor -= timedelta(days=1)
    return current, longest, reached


def _level(xp: int) -> dict:
    # Level n starts at 50·n·(n−1) XP: 0, 100, 300, 600, 1000, 1500 …
    level = 1
    while 50 * (level + 1) * level <= xp:
        level += 1
    floor, ceil = 50 * level * (level - 1), 50 * (level + 1) * level
    title = next(t for lv, t in reversed(LEVEL_TITLES) if level >= lv)
    return {"xp": xp, "level": level, "floor": floor, "next": ceil, "title": title}


def journey(db: Session, user: User) -> dict:
    lessons = db.scalars(select(Lesson).where(Lesson.user_id == user.id)).all()
    lesson_ids = [l.id for l in lessons]
    nodes = db.scalars(select(LessonNodeRow).where(LessonNodeRow.lesson_id.in_(lesson_ids))).all() if lesson_ids else []
    answers = db.scalars(
        select(Interaction).where(Interaction.lesson_id.in_(lesson_ids), Interaction.correct.is_not(None))
    ).all() if lesson_ids else []
    practice = db.scalars(select(PracticeAttempt).where(PracticeAttempt.user_id == user.id)).all()
    reports = db.scalars(select(ReportRow).where(ReportRow.user_id == user.id)).all()
    documents = db.scalars(select(Document).where(Document.user_id == user.id)).all()

    when = lambda q: q.answered_at or q.asked_at  # noqa: E731

    # ---- per-day activity ------------------------------------------------
    per: dict[date, Counter] = defaultdict(Counter)
    hours = [0] * 24
    for q in answers:
        d = _day(when(q))
        if not d:
            continue
        per[d]["answers"] += 1
        per[d]["correct"] += 1 if q.correct else 0
        per[d]["seconds"] += min(600, q.response_time_sec or 0)
        hours[_aware(when(q)).hour] += 1
    # Videos: a finished concept counts on the day it finished; one that was
    # answered but not finished counts on the day of its first answer.
    first_answer: dict = {}
    for q in answers:
        key = (q.lesson_id, q.node_id)
        if when(q) and (key not in first_answer or _aware(when(q)) < first_answer[key]):
            first_answer[key] = _aware(when(q))
    watched = []
    for n in nodes:
        if not (n.duration_sec or 0):
            continue
        stamp = n.completed_at if n.status in DONE | {"skipped"} else first_answer.get((n.lesson_id, n.node_id))
        if (d := _day(stamp)):
            watched.append(n)
            per[d]["videos"] += 1
            per[d]["seconds"] += n.duration_sec
    for p in practice:
        d = _day(p.answered_at)
        if d:
            per[d]["practice"] += 1
            per[d]["seconds"] += 30
    for l in lessons:
        if (d := _day(l.started_at or l.created_at)):
            per[d]["started"] += 1
        if l.status == "completed" and (d := _day(l.completed_at)):
            per[d]["completed"] += 1

    active = {d for d, c in per.items() if sum(c.values())}
    today = datetime.now(timezone.utc).date()
    start = max(_day(user.created_at) or today, today - timedelta(days=MAX_DAYS - 1))
    start = min([start, *active]) if active else start
    start = max(start, today - timedelta(days=MAX_DAYS - 1))
    days = []
    cursor = start
    while cursor <= today:
        c = per.get(cursor, Counter())
        days.append({
            "date": cursor.isoformat(),
            "answers": c["answers"], "correct": c["correct"], "videos": c["videos"],
            "practice": c["practice"], "started": c["started"], "completed": c["completed"],
            "minutes": round(c["seconds"] / 60, 1),
        })
        cursor += timedelta(days=1)

    current, longest, reached = _runs(active)

    # ---- mastery -----------------------------------------------------------
    status_count = Counter(n.status for n in nodes)
    mastered_nodes = [n for n in nodes if n.status in MASTERED]
    concepts = sorted(
        (
            {
                "concept": n.concept,
                "mastery_pct": round((n.mastery_score or 0) * 100),
                "attempts": n.attempts,
                "reexplains": n.times_reexplained,
                "status": n.status,
            }
            for n in nodes
            if n.attempts or n.status in DONE
        ),
        key=lambda x: x["mastery_pct"],
    )

    # First try vs rescued, per concept (same rule as the staff funnel).
    by_node: dict = defaultdict(list)
    for q in sorted(answers, key=lambda q: _aware(when(q))):
        by_node[(q.lesson_id, q.node_id)].append(q)
    first_try = sum(1 for qs in by_node.values() if qs[0].correct)
    rescued = sum(1 for qs in by_node.values() if not qs[0].correct and any(q.correct for q in qs))

    # Longest run of right answers, and when each length was first reached.
    best_row, row, row_reached = 0, 0, {}
    for q in sorted(answers, key=lambda q: _aware(when(q))):
        row = row + 1 if q.correct else 0
        best_row = max(best_row, row)
        if row:
            row_reached.setdefault(row, _day(when(q)).isoformat())

    completed = [l for l in lessons if l.status == "completed"]
    perfect = [r for r in reports if (r.score_pct or 0) >= 99.5]
    comebacks = [n for n in nodes if n.review_note in ("after help", "after review")]
    langs_done = {l.language for l in completed}
    total_minutes = round(sum(d["minutes"] for d in days))

    # ---- badges ----------------------------------------------------------------
    def tiers(group: str, value: int, earned_at) -> list[dict]:
        out = []
        for i, threshold in enumerate(BADGES[group]):
            at = earned_at(threshold) if value >= threshold else None
            out.append({
                "id": f"{group}-{threshold}", "group": group, "tier": i, "threshold": threshold,
                "value": min(value, threshold), "earned": value >= threshold, "earned_at": at,
            })
        return out

    badges: list[dict] = []
    badges += tiers("first_lesson", len(lessons), lambda n: _nth((l.created_at for l in lessons), n))
    badges += tiers("lessons_completed", len(completed), lambda n: _nth((l.completed_at for l in completed), n))
    badges += tiers("streak", longest, lambda n: reached.get(n))
    badges += tiers("active_days", len(active), lambda n: sorted(active)[n - 1].isoformat())
    badges += tiers("answers", len(answers), lambda n: _nth((when(q) for q in answers), n))
    badges += tiers("right_in_a_row", best_row, lambda n: row_reached.get(n))
    badges += tiers("concepts_mastered", len(mastered_nodes), lambda n: _nth((x.completed_at or x.updated_at for x in mastered_nodes), n))
    badges += tiers("perfect_lesson", len(perfect), lambda n: _nth((r.created_at for r in perfect), n))
    badges += tiers("comeback", len(comebacks), lambda n: _nth((x.completed_at or x.updated_at for x in comebacks), n))
    badges += tiers("own_notes", len(documents), lambda n: _nth((d.created_at for d in documents), n))
    badges += tiers("practice", len(practice), lambda n: _nth((p.answered_at for p in practice), n))
    both = 1 if {"en", "hi"} <= langs_done else 0
    badges += tiers("bilingual", both, lambda n: _nth((l.completed_at for l in completed), len(completed)))

    # Monthly badges, LeetCode-style: one per month with enough active days.
    by_month = Counter(d.strftime("%Y-%m") for d in active)
    months = [
        {"month": m, "active_days": c, "earned": c >= MONTH_BADGE_DAYS, "needed": MONTH_BADGE_DAYS}
        for m, c in sorted(by_month.items())
    ]
    this_month = today.strftime("%Y-%m")
    if this_month not in by_month:
        months.append({"month": this_month, "active_days": 0, "earned": False, "needed": MONTH_BADGE_DAYS})

    # ---- XP ------------------------------------------------------------------
    xp = (
        len(answers) * 5 + sum(1 for q in answers if q.correct) * 5 + len(completed) * 50
        + len(mastered_nodes) * 20 + len(practice) * 3 + len(active) * 10
    )

    weekday = [0] * 7
    for d in active:
        weekday[d.weekday()] += 1

    return {
        "today": today.isoformat(),
        "days": days,
        "streak": {"current": current, "longest": longest, "active_days": len(active),
                   "last_active": max(active).isoformat() if active else None},
        "level": _level(xp),
        "totals": {
            "answers": len(answers), "correct": sum(1 for q in answers if q.correct),
            "lessons_started": len(lessons), "lessons_completed": len(completed),
            "concepts_mastered": len(mastered_nodes), "practice": len(practice),
            "minutes": total_minutes, "videos": len(watched), "documents": len(documents),
            "best_right_in_a_row": best_row,
        },
        "understanding": {"concepts_checked": len(by_node), "first_try": first_try, "rescued": rescued,
                          "still_stuck": len(by_node) - first_try - rescued},
        "mastery": {
            "mastered": status_count.get("mastered", 0), "watched": status_count.get("completed", 0),
            "learning": sum(status_count.get(s, 0) for s in ("teaching", "questioning", "struggling")),
            "to_review": status_count.get("skipped", 0), "not_started": status_count.get("pending", 0),
        },
        "concepts": concepts,
        "weekday": weekday,
        "hours": hours,
        "badges": badges,
        "months": months,
    }
