"""Account management: profile, preferences, password, sessions, deletion."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.backend.src.db.base import get_db
from modules.backend.src.db.models import Lesson, RefreshToken, User, utcnow
from modules.backend.src.deps import get_current_user
from modules.backend.src.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    MessageResponse,
    SessionOut,
    UpdateProfileRequest,
    UserOut,
)
from modules.backend.src.security import (
    digest_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from modules.backend.src.services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["account"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        initials=user.initials,
        role=user.role,
        is_verified=user.is_verified,
        preferred_language=user.preferred_language,
        preferred_level=user.preferred_level,
        preferred_style=user.preferred_style,
        default_time_budget_min=user.default_time_budget_min,
        grade=user.grade,
        board=user.board,
        avatar_color=user.avatar_color,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/profile", response_model=UserOut)
def get_profile(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.patch("/profile", response_model=UserOut)
def update_profile(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not data:
        raise HTTPException(status_code=422, detail="No fields to update.")

    if "full_name" in data:
        cleaned = " ".join(data["full_name"].split())
        if len(cleaned) < 2:
            raise HTTPException(status_code=422, detail="Full name is too short.")
        data["full_name"] = cleaned

    for field, value in data.items():
        setattr(user, field, value)
    db.flush()
    return _user_out(user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Your current password is incorrect.")

    if err := validate_password_strength(payload.new_password):
        raise HTTPException(status_code=422, detail=err)

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=422, detail="Your new password must differ from the current one."
        )

    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = utcnow()
    user.token_version += 1  # invalidates every outstanding access token

    # Sign out every other device; this device re-authenticates on next refresh.
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    for token in tokens:
        token.revoked_at = utcnow()
    db.flush()

    background.add_task(email_service.send_password_changed_notice, user.email, user.full_name)
    return MessageResponse(
        message="Password changed. All devices were signed out — please sign in again."
    )


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Active sign-ins for this account, newest first."""
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .order_by(RefreshToken.created_at.desc())
    ).all()

    current_agent = (request.headers.get("user-agent") or "")[:300]
    out: list[SessionOut] = []
    seen_current = False
    for row in rows:
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        if expires < now:
            continue
        is_current = not seen_current and row.user_agent == current_agent
        if is_current:
            seen_current = True
        out.append(
            SessionOut(
                id=row.id,
                user_agent=row.user_agent,
                ip_address=row.ip_address,
                created_at=row.created_at,
                last_used_at=row.last_used_at,
                expires_at=row.expires_at,
                current=is_current,
            )
        )
    return out


@router.delete("/sessions/{session_row_id}", response_model=MessageResponse)
def revoke_session(
    session_row_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(RefreshToken, session_row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    if row.revoked_at is None:
        row.revoked_at = utcnow()
        db.flush()
    return MessageResponse(message="That device has been signed out.")


@router.post("/sessions/revoke-all", response_model=MessageResponse)
def revoke_all_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    for token in tokens:
        token.revoked_at = utcnow()
    db.flush()
    return MessageResponse(message=f"Signed out of {len(tokens)} device(s).")


@router.delete("/", response_model=MessageResponse)
def delete_account(
    payload: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete the account and every lesson, document, and report it owns."""
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password is incorrect.")

    lesson_count = db.scalar(
        select(Lesson).where(Lesson.user_id == user.id).exists().select()
    )
    logger.info("Deleting account %s (had lessons: %s)", user.id, bool(lesson_count))

    db.delete(user)  # cascades to lessons, nodes, interactions, reports, tokens
    db.flush()
    return MessageResponse(message="Your account and all associated data have been deleted.")
