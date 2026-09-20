"""End-to-end authentication: signup, OTP, login, refresh rotation, reset."""
import pytest

from modules.backend.src.config import settings
from modules.backend.src.db.models import OTPCode, User
from sqlalchemy import select

API = "/api/v1/auth"


def test_signup_returns_otp_and_creates_unverified_user(client, signup_payload, db):
    response = client.post(f"{API}/signup", json=signup_payload)
    assert response.status_code == 201
    assert len(response.json()["dev_otp"]) == settings.otp_length

    user = db.scalars(select(User).where(User.email == signup_payload["email"])).first()
    assert user is not None
    assert user.is_verified is False
    assert user.password_hash != signup_payload["password"], "password must never be stored raw"


def test_signup_normalises_email_case(client, signup_payload, db):
    signup_payload["email"] = "Learner@Example.COM"
    client.post(f"{API}/signup", json=signup_payload)
    assert db.scalars(select(User).where(User.email == "learner@example.com")).first()


def test_signup_rejects_weak_password(client, signup_payload):
    signup_payload["password"] = "weakpass"
    response = client.post(f"{API}/signup", json=signup_payload)
    assert response.status_code == 422
    assert "uppercase" in response.json()["detail"]


def test_signup_rejects_invalid_email(client, signup_payload):
    signup_payload["email"] = "not-an-email"
    assert client.post(f"{API}/signup", json=signup_payload).status_code == 422


def test_duplicate_verified_signup_is_rejected(client, signup_payload, verified_user):
    response = client.post(f"{API}/signup", json=signup_payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_unverified_signup_can_be_retried(client, signup_payload):
    """Re-registering an unverified email updates it rather than creating a duplicate."""
    client.post(f"{API}/signup", json=signup_payload)
    signup_payload["full_name"] = "Corrected Name"
    second = client.post(f"{API}/signup", json=signup_payload)
    assert second.status_code == 201

    code = second.json()["dev_otp"]
    verified = client.post(
        f"{API}/verify-email", json={"email": signup_payload["email"], "code": code}
    )
    assert verified.json()["user"]["full_name"] == "Corrected Name"


def test_login_blocked_until_email_is_verified(client, signup_payload):
    client.post(f"{API}/signup", json=signup_payload)
    response = client.post(
        f"{API}/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert response.status_code == 403
    assert "verify" in response.json()["detail"].lower()


def test_wrong_otp_reports_remaining_attempts(client, signup_payload):
    client.post(f"{API}/signup", json=signup_payload)
    response = client.post(
        f"{API}/verify-email", json={"email": signup_payload["email"], "code": "000000"}
    )
    assert response.status_code == 400
    assert "remaining" in response.json()["detail"]


def test_otp_locks_out_after_max_attempts(client, signup_payload):
    client.post(f"{API}/signup", json=signup_payload)
    for _ in range(settings.otp_max_attempts):
        client.post(
            f"{API}/verify-email", json={"email": signup_payload["email"], "code": "000000"}
        )
    response = client.post(
        f"{API}/verify-email", json={"email": signup_payload["email"], "code": "000000"}
    )
    assert response.status_code == 400
    assert "Request a new code" in response.json()["detail"]


def test_otp_is_single_use(client, signup_payload):
    signup = client.post(f"{API}/signup", json=signup_payload)
    code = signup.json()["dev_otp"]
    body = {"email": signup_payload["email"], "code": code}

    assert client.post(f"{API}/verify-email", json=body).status_code == 200
    assert client.post(f"{API}/verify-email", json=body).status_code == 400


def test_resending_an_otp_invalidates_the_previous_one(client, signup_payload):
    first = client.post(f"{API}/signup", json=signup_payload).json()["dev_otp"]
    second = client.post(
        f"{API}/resend-otp",
        json={"email": signup_payload["email"], "purpose": "verify_email"},
    ).json()["dev_otp"]
    assert first != second

    stale = client.post(
        f"{API}/verify-email", json={"email": signup_payload["email"], "code": first}
    )
    assert stale.status_code == 400
    assert (
        client.post(
            f"{API}/verify-email", json={"email": signup_payload["email"], "code": second}
        ).status_code
        == 200
    )


def test_verification_returns_working_tokens(client, verified_user):
    assert verified_user["token_type"] == "bearer"
    assert verified_user["user"]["is_verified"] is True

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {verified_user['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == verified_user["user"]["email"]


def test_login_succeeds_after_verification(client, signup_payload, verified_user):
    response = client.post(
        f"{API}/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert response.status_code == 200
    assert response.json()["user"]["initials"] == "TL"


def test_login_rejects_wrong_password(client, signup_payload, verified_user):
    response = client.post(
        f"{API}/login", json={"email": signup_payload["email"], "password": "WrongPass9"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_login_does_not_reveal_whether_an_account_exists(client, signup_payload, verified_user):
    """The same message for an unknown email and a wrong password."""
    unknown = client.post(
        f"{API}/login", json={"email": "nobody@example.com", "password": "Whatever1"}
    )
    wrong = client.post(
        f"{API}/login", json={"email": signup_payload["email"], "password": "Whatever1"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_account_locks_after_repeated_failures(client, signup_payload, verified_user, db):
    for _ in range(settings.max_failed_logins):
        client.post(
            f"{API}/login", json={"email": signup_payload["email"], "password": "WrongPass9"}
        )
    response = client.post(
        f"{API}/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert response.status_code == 423
    assert "locked" in response.json()["detail"].lower()


def test_refresh_rotates_the_token(client, verified_user):
    original = verified_user["refresh_token"]
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert response.status_code == 200

    rotated = response.json()["refresh_token"]
    assert rotated != original

    replayed = client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert replayed.status_code == 401


def test_replaying_a_used_refresh_token_kills_every_session(client, verified_user):
    """Replay suggests theft, so all of that user's sessions are revoked."""
    original = verified_user["refresh_token"]
    rotated = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original}
    ).json()["refresh_token"]

    client.post("/api/v1/auth/refresh", json={"refresh_token": original})  # the replay

    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": rotated}).status_code == 401
    )


def test_logout_revokes_the_refresh_token(client, verified_user):
    token = verified_user["refresh_token"]
    assert client.post("/api/v1/auth/logout", json={"refresh_token": token}).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 401


def test_forgot_password_answers_identically_for_unknown_emails(client, verified_user):
    known = client.post(f"{API}/forgot-password", json={"email": "learner@example.com"})
    unknown = client.post(f"{API}/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]


def test_password_reset_end_to_end(client, signup_payload, verified_user):
    code = client.post(
        f"{API}/forgot-password", json={"email": signup_payload["email"]}
    ).json()["dev_otp"]

    reset = client.post(
        f"{API}/reset-password",
        json={
            "email": signup_payload["email"],
            "code": code,
            "new_password": "BrandNewPass9",
        },
    )
    assert reset.status_code == 200

    assert (
        client.post(
            f"{API}/login",
            json={"email": signup_payload["email"], "password": signup_payload["password"]},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{API}/login",
            json={"email": signup_payload["email"], "password": "BrandNewPass9"},
        ).status_code
        == 200
    )


def test_reset_rejects_reusing_the_current_password(client, signup_payload, verified_user):
    code = client.post(
        f"{API}/forgot-password", json={"email": signup_payload["email"]}
    ).json()["dev_otp"]

    response = client.post(
        f"{API}/reset-password",
        json={
            "email": signup_payload["email"],
            "code": code,
            "new_password": signup_payload["password"],
        },
    )
    assert response.status_code == 422
    assert "differ" in response.json()["detail"]


def test_reset_revokes_existing_sessions(client, signup_payload, verified_user):
    """A reset exists to lock an attacker out, so old sessions must die with it."""
    old_refresh = verified_user["refresh_token"]
    code = client.post(
        f"{API}/forgot-password", json={"email": signup_payload["email"]}
    ).json()["dev_otp"]
    client.post(
        f"{API}/reset-password",
        json={"email": signup_payload["email"], "code": code, "new_password": "BrandNewPass9"},
    )

    assert (
        client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh}).status_code
        == 401
    )


def test_access_token_issued_before_a_reset_stops_working(
    client, signup_payload, verified_user
):
    headers = {"Authorization": f"Bearer {verified_user['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    code = client.post(
        f"{API}/forgot-password", json={"email": signup_payload["email"]}
    ).json()["dev_otp"]
    client.post(
        f"{API}/reset-password",
        json={"email": signup_payload["email"], "code": code, "new_password": "BrandNewPass9"},
    )

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_protected_routes_require_a_token(client):
    for path in ("/api/v1/auth/me", "/api/v1/dashboard", "/api/v1/lessons"):
        assert client.get(path).status_code == 401


def test_protected_routes_reject_a_forged_token(client):
    headers = {"Authorization": "Bearer made.up.token"}
    assert client.get("/api/v1/dashboard", headers=headers).status_code == 401
