"""Password hashing, token integrity, and OTP primitives."""
import time

import pytest

from modules.backend.src.security import (
    create_access_token,
    create_ws_ticket,
    decode_token,
    digest_token,
    generate_opaque_token,
    generate_otp,
    hash_otp,
    hash_password,
    validate_password_strength,
    verify_otp,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("Shikshak2026")
    second = hash_password("Shikshak2026")
    assert first != second, "each hash must use a fresh salt"
    assert verify_password("Shikshak2026", first)
    assert verify_password("Shikshak2026", second)


def test_password_hash_rejects_wrong_password():
    assert not verify_password("WrongPass1", hash_password("Shikshak2026"))


def test_verify_password_survives_malformed_hash():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_long_passwords_are_not_silently_truncated():
    """bcrypt ignores bytes past 72; pre-hashing keeps the whole password significant."""
    base = "A1" + "x" * 100
    stored = hash_password(base + "-first-ending")
    assert not verify_password(base + "-second-ending", stored)
    assert verify_password(base + "-first-ending", stored)


@pytest.mark.parametrize(
    "password",
    ["short1A", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere", "x" * 129],
)
def test_weak_passwords_are_rejected(password):
    assert validate_password_strength(password) is not None


def test_strong_password_is_accepted():
    assert validate_password_strength("Shikshak2026") is None


def test_access_token_round_trip():
    token = create_access_token("user-123", "a@b.com")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["email"] == "a@b.com"


def test_token_type_is_enforced():
    """A WS ticket must never be usable as an access token, or vice versa."""
    ticket = create_ws_ticket("user-123", "lesson-1")
    assert decode_token(ticket, expected_type="access") is None
    assert decode_token(ticket, expected_type="ws_ticket")["lesson_id"] == "lesson-1"

    access = create_access_token("user-123", "a@b.com")
    assert decode_token(access, expected_type="ws_ticket") is None


def test_tampered_token_is_rejected():
    token = create_access_token("user-123", "a@b.com")
    head, body, sig = token.split(".")
    assert decode_token(f"{head}.{body}.{sig[:-3]}abc", expected_type="access") is None


def test_garbage_token_is_rejected():
    assert decode_token("not-a-jwt", expected_type="access") is None
    assert decode_token("", expected_type="access") is None


def test_otp_is_numeric_and_correct_length():
    code = generate_otp(6)
    assert len(code) == 6 and code.isdigit()


def test_otp_hash_verifies_only_the_right_code():
    code = generate_otp()
    stored = hash_otp(code)
    assert verify_otp(code, stored)
    assert not verify_otp("000000", stored)


def test_opaque_tokens_are_unique_and_digest_stably():
    a, b = generate_opaque_token(), generate_opaque_token()
    assert a != b
    assert digest_token(a) == digest_token(a)
    assert digest_token(a) != digest_token(b)
    # The digest must not leak the token itself.
    assert a not in digest_token(a)
