"""Shared FastAPI dependencies: current user resolution and rate limiting."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from modules.backend.src.config import settings
from modules.backend.src.db.base import get_db
from modules.backend.src.db.models import RateLimitEntry, User
from modules.backend.src.security import decode_token

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated, verified, active user from a Bearer access token or query parameter."""
    raw_token = (
        credentials.credentials
        if credentials and credentials.credentials
        else request.query_params.get("token")
    )
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not raw_token:
        raise unauthorized

    payload = decode_token(raw_token, expected_type="access")
    if not payload:
        raise unauthorized

    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise unauthorized
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email address is not verified"
        )

    # Tokens minted before the last password change are rejected. Comparing
    # versions rather than timestamps avoids the one-second window in which a
    # stale token and the password change share an `iat`.
    if payload.get("ver", 1) != user.token_version:
        raise unauthorized

    return user


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    try:
        return get_current_user(request, credentials, db)
    except HTTPException:
        return None


def client_ip(request: Request) -> str:
    """Identify the caller for rate limiting.

    X-Forwarded-For is read only when settings.trust_proxy_headers says a proxy
    sets it. Otherwise any client could forge a fresh address per request and
    bypass every limit here.
    """
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Sliding-window limiter persisted in SQLite so limits survive restarts."""

    def __init__(self, max_calls: int, window_sec: int, scope: str):
        self.max_calls = max_calls
        self.window_sec = window_sec
        self.scope = scope

    def check(self, db: Session, key: str) -> None:
        bucket = f"{self.scope}:{key}"
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_sec)

        # Opportunistic cleanup of entries that can no longer affect any window.
        db.execute(
            delete(RateLimitEntry).where(
                RateLimitEntry.occurred_at < now - timedelta(seconds=self.window_sec * 4)
            )
        )

        count = db.scalar(
            select(func.count())
            .select_from(RateLimitEntry)
            .where(RateLimitEntry.bucket == bucket, RateLimitEntry.occurred_at >= window_start)
        ) or 0

        if count >= self.max_calls:
            retry_after = self.window_sec
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )

        db.add(RateLimitEntry(bucket=bucket, occurred_at=now))
        db.flush()


# Tuned to stop credential stuffing and OTP brute force without blocking real use.
login_limiter = RateLimiter(max_calls=10, window_sec=300, scope="login")
signup_limiter = RateLimiter(max_calls=5, window_sec=3600, scope="signup")
otp_send_limiter = RateLimiter(max_calls=5, window_sec=900, scope="otp_send")
otp_verify_limiter = RateLimiter(max_calls=12, window_sec=900, scope="otp_verify")
reset_limiter = RateLimiter(max_calls=5, window_sec=900, scope="reset")
