"""SQLAlchemy ORM models backing accounts, lessons, and progress tracking."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from modules.backend.src.db.base import Base, UTCDateTime


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


# --------------------------------------------------------------------------
# Accounts & authentication
# --------------------------------------------------------------------------

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="student", nullable=False)

    # Learner preferences (drive lesson defaults)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    preferred_level: Mapped[str] = mapped_column(String(20), default="beginner", nullable=False)
    preferred_style: Mapped[Optional[str]] = mapped_column(String(40), default="visual")
    default_time_budget_min: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    grade: Mapped[Optional[str]] = mapped_column(String(40))
    board: Mapped[Optional[str]] = mapped_column(String(40))
    avatar_color: Mapped[str] = mapped_column(String(7), default="#2A3FA0", nullable=False)

    # Security posture
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    password_changed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    # Bumped on every password change. Embedded in access tokens so older ones
    # are rejected immediately, without depending on second-granular clocks.
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    otps: Mapped[list["OTPCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped[Optional["LearnerProfileRow"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    @property
    def initials(self) -> str:
        parts = [p for p in self.full_name.split() if p]
        if not parts:
            return self.email[:2].upper()
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()


class OTPCode(Base):
    """Single-use, hashed, expiring one-time codes for email verification and reset."""

    __tablename__ = "otp_codes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)  # verify_email | reset_password
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="otps")

    __table_args__ = (Index("ix_otp_user_purpose", "user_id", "purpose"),)


class RefreshToken(Base):
    """Rotating refresh tokens; stores only a SHA-256 digest of the token."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    user_agent: Mapped[Optional[str]] = mapped_column(String(300))
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class RateLimitEntry(Base):
    """Persistent sliding-window counters for auth endpoint throttling."""

    __tablename__ = "rate_limits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False, index=True)


# --------------------------------------------------------------------------
# Documents & lessons
# --------------------------------------------------------------------------

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ingesting", nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text)
    source_lang: Mapped[Optional[str]] = mapped_column(String(10))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chapters: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    key_terms: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    user: Mapped["User"] = relationship(back_populates="documents")


class Lesson(Base, TimestampMixin):
    """One teaching session: plan, live state, and final outcome."""

    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Token used to authorise the live WebSocket for this lesson.
    session_token_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="topic", nullable=False)  # topic|document
    topic: Mapped[Optional[str]] = mapped_column(Text)
    document_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True
    )

    level: Mapped[str] = mapped_column(String(20), default="beginner", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    time_budget_min: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    style: Mapped[Optional[str]] = mapped_column(String(40))

    plan_lesson_id: Mapped[Optional[str]] = mapped_column(String(120))
    plan_json: Mapped[Optional[dict]] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(String(20), default="created", nullable=False)
    # created | planned | in_progress | completed | escalated | abandoned
    fsm_state: Mapped[str] = mapped_column(String(30), default="CREATED", nullable=False)
    current_node_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    total_watch_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="lessons")
    document: Mapped[Optional["Document"]] = relationship(lazy="joined")
    nodes: Mapped[list["LessonNodeRow"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", order_by="LessonNodeRow.position"
    )
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )
    report: Mapped[Optional["ReportRow"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan", uselist=False
    )
    events: Mapped[list["LessonEvent"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_lesson_user_status", "user_id", "status"),)


class LessonNodeRow(Base, TimestampMixin):
    """Per-concept progress within a lesson — the unit we track mastery on."""

    __tablename__ = "lesson_nodes"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(80), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    concept: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[str] = mapped_column(String(20), default="core", nullable=False)
    est_minutes: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    visual_type: Mapped[str] = mapped_column(String(30), default="diagram", nullable=False)
    checkpoint_question: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # pending | teaching | questioning | mastered | struggling | skipped
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    times_reexplained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    script_text: Mapped[Optional[str]] = mapped_column(Text)
    video_url: Mapped[Optional[str]] = mapped_column(String(600))
    video_path: Mapped[Optional[str]] = mapped_column(String(600))
    captions_url: Mapped[Optional[str]] = mapped_column(String(600))
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    citation_json: Mapped[Optional[dict]] = mapped_column(JSON)

    first_seen_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    lesson: Mapped["Lesson"] = relationship(back_populates="nodes")

    __table_args__ = (UniqueConstraint("lesson_id", "node_id", name="uq_lesson_node"),)


class Interaction(Base):
    """A checkpoint question, the learner's answer, and how it was graded."""

    __tablename__ = "interactions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(40), nullable=False)
    options: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    expected_concept: Mapped[str] = mapped_column(Text, default="", nullable=False)

    raw_answer: Mapped[Optional[str]] = mapped_column(Text)
    response_time_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    partial_credit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    misconception_tag: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text)
    adaptation_action: Mapped[Optional[str]] = mapped_column(String(20))
    adaptation_reason: Mapped[Optional[str]] = mapped_column(Text)

    asked_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    answered_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    lesson: Mapped["Lesson"] = relationship(back_populates="interactions")


class ReportRow(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    score_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    strong_areas: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    weak_areas: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    recommended_next: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    narrative_feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)

    lesson: Mapped["Lesson"] = relationship(back_populates="report")


class LessonEvent(Base):
    """Append-only timeline of everything that happened in a lesson."""

    __tablename__ = "lesson_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[str] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    node_id: Mapped[Optional[str]] = mapped_column(String(80))
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False, index=True)

    lesson: Mapped["Lesson"] = relationship(back_populates="events")


class LearnerProfileRow(Base, TimestampMixin):
    """Rolling, cross-lesson mastery picture used by the dashboard and planner."""

    __tablename__ = "learner_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    strong_concepts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    weak_concepts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    current_learning_path: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    misconception_counts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    lessons_started: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_learning_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[Optional[str]] = mapped_column(String(10))

    user: Mapped["User"] = relationship(back_populates="profile")
