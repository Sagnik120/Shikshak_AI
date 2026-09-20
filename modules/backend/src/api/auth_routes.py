"""Authentication: signup, email OTP verification, login, refresh, password reset."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.backend.src.config import settings
from modules.backend.src.db.base import get_db
from modules.backend.src.db.models import (
    LearnerProfileRow,
    OTPCode,
    RefreshToken,
    User,
    utcnow,
)
from modules.backend.src.deps import (
    client_ip,
    get_current_user,
    login_limiter,
    otp_send_limiter,
    otp_verify_limiter,
    reset_limiter,
    signup_limiter,
)
from modules.backend.src.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
    VerifyOTPRequest,
)
from modules.backend.src.security import (
    access_token_expires_in,
    create_access_token,
    digest_token,
    generate_opaque_token,
    generate_otp,
    hash_otp,
    hash_password,
    otp_expiry,
    refresh_token_expiry,
    validate_password_strength,
    verify_otp,
    verify_password,
)
from modules.backend.src.services.email_service import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

PURPOSE_VERIFY = "verify_email"
PURPOSE_RESET = "reset_password"

# Generic response for email-enumeration-sensitive endpoints.
_GENERIC_RESET_MSG = (
    "If an account exists for that email, we've sent a reset code. Check your inbox."
)


def _persist_and_raise(db: Session, exc: HTTPException) -> None:
    """Commit security side effects, then raise.

    The request-scoped session rolls back when a handler raises, which would
    otherwise discard the very counters these failures exist to record:
    OTP attempts, failed logins, lockouts, and token revocations.
    """
    db.commit()
    raise exc


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; normalise to UTC before comparing."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _normalise_email(email: str) -> str:
    return email.strip().lower()


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


def _issue_tokens(db: Session, user: User, request: Request) -> TokenResponse:
    """Mint an access token plus a fresh stored refresh token for this device."""
    raw_refresh = generate_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest_token(raw_refresh),
            expires_at=refresh_token_expiry(),
            user_agent=(request.headers.get("user-agent") or "")[:300],
            ip_address=client_ip(request)[:64],
        )
    )
    user.last_login_at = utcnow()
    user.failed_login_count = 0
    user.locked_until = None
    db.flush()

    return TokenResponse(
        access_token=create_access_token(user.id, user.email, user.token_version),
        refresh_token=raw_refresh,
        expires_in=access_token_expires_in(),
        user=_user_out(user),
    )


def _issue_otp(db: Session, user: User, purpose: str) -> str:
    """Invalidate outstanding codes for this purpose and mint a new one."""
    now = utcnow()
    outstanding = db.scalars(
        select(OTPCode).where(
            OTPCode.user_id == user.id,
            OTPCode.purpose == purpose,
            OTPCode.consumed_at.is_(None),
        )
    ).all()
    for old in outstanding:
        old.consumed_at = now

    code = generate_otp()
    db.add(
        OTPCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=hash_otp(code),
            expires_at=otp_expiry(),
        )
    )
    db.flush()
    return code


def _cooldown_remaining(db: Session, user: User, purpose: str) -> int:
    latest = db.scalars(
        select(OTPCode)
        .where(OTPCode.user_id == user.id, OTPCode.purpose == purpose)
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    ).first()
    if not latest:
        return 0
    created = _aware(latest.created_at)
    elapsed = (datetime.now(timezone.utc) - created).total_seconds()
    remaining = settings.otp_resend_cooldown_sec - elapsed
    return max(0, int(remaining))


def _consume_otp(db: Session, user: User, purpose: str, code: str) -> None:
    """Validate a submitted code, raising a 400 with a specific reason on failure."""
    record = db.scalars(
        select(OTPCode)
        .where(
            OTPCode.user_id == user.id,
            OTPCode.purpose == purpose,
            OTPCode.consumed_at.is_(None),
        )
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    ).first()

    if not record:
        raise HTTPException(
            status_code=400, detail="No active code. Request a new one."
        )

    if _aware(record.expires_at) < datetime.now(timezone.utc):
        record.consumed_at = utcnow()
        _persist_and_raise(
            db,
            HTTPException(status_code=400, detail="This code has expired. Request a new one."),
        )

    if record.attempts >= settings.otp_max_attempts:
        record.consumed_at = utcnow()
        _persist_and_raise(
            db,
            HTTPException(
                status_code=400, detail="Too many incorrect attempts. Request a new code."
            ),
        )

    if not verify_otp(code.strip(), record.code_hash):
        record.attempts += 1
        left = settings.otp_max_attempts - record.attempts
        _persist_and_raise(
            db,
            HTTPException(
                status_code=400,
                detail=f"Incorrect code. {left} attempt{'s' if left != 1 else ''} remaining.",
            ),
        )

    record.consumed_at = utcnow()
    db.flush()


def _dev_otp(code: str) -> Optional[str]:
    """Expose the code only when explicitly enabled (e.g. automated test suites) and SMTP is unconfigured."""
    if not settings.expose_dev_otp:
        return None
    return None if settings.smtp_configured else code


def _revoke_all_refresh_tokens(db: Session, user_id: str, keep_hash: Optional[str] = None) -> None:
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    now = utcnow()
    for token in tokens:
        if keep_hash and token.token_hash == keep_hash:
            continue
        token.revoked_at = now


# --------------------------------------------------------------------------
# Signup & verification
# --------------------------------------------------------------------------

@router.post("/signup", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    signup_limiter.check(db, client_ip(request))

    if err := validate_password_strength(payload.password):
        raise HTTPException(status_code=422, detail=err)

    email = _normalise_email(payload.email)
    existing = db.scalars(select(User).where(User.email == email)).first()

    if existing and existing.is_verified:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Try signing in instead.",
        )

    if existing:
        # Unverified signup being retried: refresh the details rather than duplicating.
        existing.full_name = payload.full_name
        existing.password_hash = hash_password(payload.password)
        existing.grade = payload.grade
        existing.board = payload.board
        existing.preferred_language = payload.preferred_language
        existing.preferred_level = payload.preferred_level
        user = existing
    else:
        user = User(
            email=email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            grade=payload.grade,
            board=payload.board,
            preferred_language=payload.preferred_language,
            preferred_level=payload.preferred_level,
        )
        db.add(user)
        db.flush()
        db.add(LearnerProfileRow(user_id=user.id))

    code = _issue_otp(db, user, PURPOSE_VERIFY)
    db.flush()
    background.add_task(email_service.send_verification_otp, user.email, user.full_name, code)

    return MessageResponse(
        message=f"We sent a {settings.otp_length}-digit code to {user.email}. "
        f"It expires in {settings.otp_ttl_min} minutes.",
        dev_otp=_dev_otp(code),
    )


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(
    payload: VerifyOTPRequest,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    otp_verify_limiter.check(db, client_ip(request))

    email = _normalise_email(payload.email)
    user = db.scalars(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code.")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="This email is already verified. Please sign in.")

    _consume_otp(db, user, PURPOSE_VERIFY, payload.code)

    user.is_verified = True
    if not user.profile:
        db.add(LearnerProfileRow(user_id=user.id))
    db.flush()

    background.add_task(email_service.send_welcome, user.email, user.full_name)
    return _issue_tokens(db, user, request)


@router.post("/resend-otp", response_model=MessageResponse)
def resend_otp(
    payload: ResendOTPRequest,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    otp_send_limiter.check(db, client_ip(request))

    email = _normalise_email(payload.email)
    user = db.scalars(select(User).where(User.email == email)).first()

    generic = MessageResponse(message="If that account exists, a new code is on its way.")
    if not user:
        return generic

    if payload.purpose == PURPOSE_VERIFY and user.is_verified:
        raise HTTPException(status_code=400, detail="This email is already verified.")

    if remaining := _cooldown_remaining(db, user, payload.purpose):
        raise HTTPException(
            status_code=429,
            detail=f"Please wait {remaining}s before requesting another code.",
            headers={"Retry-After": str(remaining)},
        )

    code = _issue_otp(db, user, payload.purpose)
    db.flush()

    if payload.purpose == PURPOSE_VERIFY:
        background.add_task(email_service.send_verification_otp, user.email, user.full_name, code)
    else:
        background.add_task(email_service.send_password_reset_otp, user.email, user.full_name, code)

    return MessageResponse(
        message=f"A new code was sent to {user.email}.", dev_otp=_dev_otp(code)
    )


# --------------------------------------------------------------------------
# Login / refresh / logout
# --------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    login_limiter.check(db, client_ip(request))

    email = _normalise_email(payload.email)
    user = db.scalars(select(User).where(User.email == email)).first()

    invalid = HTTPException(status_code=401, detail="Incorrect email or password.")

    if not user:
        # Constant-ish work so timing doesn't reveal whether the email exists.
        verify_password(payload.password, hash_password("dummy-password-A1"))
        raise invalid

    locked_until = _aware(user.locked_until)
    if locked_until and locked_until > datetime.now(timezone.utc):
        mins = max(1, int((locked_until - datetime.now(timezone.utc)).total_seconds() // 60) + 1)
        raise HTTPException(
            status_code=423,
            detail=f"Account temporarily locked after too many failed attempts. "
            f"Try again in {mins} minute{'s' if mins != 1 else ''}.",
        )

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.max_failed_logins:
            user.locked_until = utcnow() + timedelta(minutes=settings.lockout_minutes)
            user.failed_login_count = 0
        _persist_and_raise(db, invalid)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before signing in. Check your inbox for the code.",
        )

    return _issue_tokens(db, user, request)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    """Rotate the refresh token: the presented one is revoked and replaced."""
    token_hash = digest_token(payload.refresh_token)
    record = db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()

    invalid = HTTPException(status_code=401, detail="Session expired. Please sign in again.")

    if not record or record.revoked_at is not None:
        if record and record.revoked_at is not None:
            # A revoked token being replayed suggests theft — drop every session.
            logger.warning(
                "Replayed refresh token for user %s; revoking all sessions", record.user_id
            )
            _revoke_all_refresh_tokens(db, record.user_id)
            _persist_and_raise(db, invalid)
        raise invalid

    if _aware(record.expires_at) < datetime.now(timezone.utc):
        record.revoked_at = utcnow()
        _persist_and_raise(db, invalid)

    user = db.get(User, record.user_id)
    if not user or not user.is_active or not user.is_verified:
        raise invalid

    record.revoked_at = utcnow()
    record.last_used_at = utcnow()
    db.flush()
    return _issue_tokens(db, user, request)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    record = db.scalars(
        select(RefreshToken).where(RefreshToken.token_hash == digest_token(payload.refresh_token))
    ).first()
    if record and record.revoked_at is None:
        record.revoked_at = utcnow()
    return MessageResponse(message="Signed out.")


# --------------------------------------------------------------------------
# Password reset
# --------------------------------------------------------------------------

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    reset_limiter.check(db, client_ip(request))

    email = _normalise_email(payload.email)
    user = db.scalars(select(User).where(User.email == email)).first()

    # Always answer identically so this endpoint can't enumerate accounts.
    if not user or not user.is_active:
        return MessageResponse(message=_GENERIC_RESET_MSG)

    if _cooldown_remaining(db, user, PURPOSE_RESET):
        return MessageResponse(message=_GENERIC_RESET_MSG)

    code = _issue_otp(db, user, PURPOSE_RESET)
    db.flush()
    background.add_task(email_service.send_password_reset_otp, user.email, user.full_name, code)

    return MessageResponse(message=_GENERIC_RESET_MSG, dev_otp=_dev_otp(code))


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    otp_verify_limiter.check(db, client_ip(request))

    if err := validate_password_strength(payload.new_password):
        raise HTTPException(status_code=422, detail=err)

    email = _normalise_email(payload.email)
    user = db.scalars(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code.")

    _consume_otp(db, user, PURPOSE_RESET, payload.code)

    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=422, detail="Your new password must differ from the current one."
        )

    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = utcnow()
    user.token_version += 1  # invalidates every outstanding access token
    user.failed_login_count = 0
    user.locked_until = None
    # A reset invalidates every existing session on every device.
    _revoke_all_refresh_tokens(db, user.id)
    db.flush()

    background.add_task(email_service.send_password_changed_notice, user.email, user.full_name)
    return MessageResponse(message="Password updated. You can now sign in with your new password.")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)
