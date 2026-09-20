"""Password hashing, JWT issuance/verification, OTP generation, and token digests."""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from modules.backend.src.config import settings

# bcrypt truncates silently past 72 bytes, so pre-hash to keep full entropy.
_BCRYPT_ROUNDS = 12


def _prehash(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt(_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


PASSWORD_RULES = (
    "Password must be at least 8 characters and include an uppercase letter, "
    "a lowercase letter, and a number."
)


def validate_password_strength(password: str) -> Optional[str]:
    """Return an error message, or None when the password is acceptable."""
    if len(password) < 8:
        return PASSWORD_RULES
    if len(password) > 128:
        return "Password must be at most 128 characters."
    if not re.search(r"[a-z]", password):
        return PASSWORD_RULES
    if not re.search(r"[A-Z]", password):
        return PASSWORD_RULES
    if not re.search(r"\d", password):
        return PASSWORD_RULES
    return None


# --------------------------------------------------------------------------
# Opaque token digests (refresh tokens, lesson session tokens)
# --------------------------------------------------------------------------

def generate_opaque_token(nbytes: int = 48) -> str:
    return secrets.token_urlsafe(nbytes)


def digest_token(token: str) -> str:
    """Keyed digest so a database leak alone cannot reconstruct valid tokens."""
    return hmac.new(
        settings.secret_key.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


# --------------------------------------------------------------------------
# OTP codes
# --------------------------------------------------------------------------

def generate_otp(length: Optional[int] = None) -> str:
    n = length or settings.otp_length
    return "".join(secrets.choice("0123456789") for _ in range(n))


def hash_otp(code: str) -> str:
    return digest_token(f"otp:{code}")


def verify_otp(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(code), code_hash)


# --------------------------------------------------------------------------
# JWT access tokens + short-lived WebSocket tickets
# --------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: str, email: str, token_version: int = 1, extra: Optional[dict] = None
) -> str:
    expires = _now() + timedelta(minutes=settings.access_token_ttl_min)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "ver": token_version,
        "type": "access",
        "iat": int(_now().timestamp()),
        "exp": int(expires.timestamp()),
        "jti": secrets.token_hex(8),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_ws_ticket(user_id: str, lesson_id: str) -> str:
    """One-purpose short-lived token so the WS URL never carries a real access token."""
    expires = _now() + timedelta(seconds=settings.ws_ticket_ttl_sec)
    payload = {
        "sub": user_id,
        "lesson_id": lesson_id,
        "type": "ws_ticket",
        "iat": int(_now().timestamp()),
        "exp": int(expires.timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str) -> Optional[dict]:
    """Decode and validate a JWT, returning None on any failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def access_token_expires_in() -> int:
    return settings.access_token_ttl_min * 60


def refresh_token_expiry() -> datetime:
    return _now() + timedelta(days=settings.refresh_token_ttl_days)


def otp_expiry() -> datetime:
    return _now() + timedelta(minutes=settings.otp_ttl_min)
