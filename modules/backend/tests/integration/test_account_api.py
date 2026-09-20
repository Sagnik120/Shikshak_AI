"""Account management: profile, preferences, password change, sessions, deletion."""
import pytest
from sqlalchemy import select

from modules.backend.src.db.models import Lesson, RefreshToken, User

API = "/api/v1"


def test_profile_returns_the_signed_in_user(client, auth_headers, signup_payload):
    body = client.get(f"{API}/account/profile", headers=auth_headers).json()
    assert body["email"] == signup_payload["email"]
    assert body["grade"] == "Class 10"
    assert body["initials"] == "TL"


def test_profile_update_persists(client, auth_headers):
    response = client.patch(
        f"{API}/account/profile",
        headers=auth_headers,
        json={
            "full_name": "Renamed Learner",
            "preferred_level": "advanced",
            "preferred_language": "bn",
            "default_time_budget_min": 30,
            "avatar_color": "#0FA3A3",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Renamed Learner"
    assert body["preferred_level"] == "advanced"
    assert body["default_time_budget_min"] == 30
    assert body["initials"] == "RL"

    # And it survives a re-read.
    assert client.get(f"{API}/account/profile", headers=auth_headers).json()["preferred_language"] == "bn"


def test_profile_update_rejects_an_invalid_colour(client, auth_headers):
    response = client.patch(
        f"{API}/account/profile", headers=auth_headers, json={"avatar_color": "red"}
    )
    assert response.status_code == 422


def test_profile_update_rejects_an_out_of_range_time_budget(client, auth_headers):
    response = client.patch(
        f"{API}/account/profile", headers=auth_headers, json={"default_time_budget_min": 500}
    )
    assert response.status_code == 422


def test_empty_profile_update_is_rejected(client, auth_headers):
    assert client.patch(f"{API}/account/profile", headers=auth_headers, json={}).status_code == 422


def test_profile_update_requires_authentication(client):
    assert client.patch(f"{API}/account/profile", json={"full_name": "X Y"}).status_code == 401


# --- Password change -------------------------------------------------------

def test_change_password_requires_the_current_one(client, auth_headers):
    response = client.post(
        f"{API}/account/change-password",
        headers=auth_headers,
        json={"current_password": "WrongPass9", "new_password": "BrandNewPass9"},
    )
    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


def test_change_password_enforces_strength(client, auth_headers):
    response = client.post(
        f"{API}/account/change-password",
        headers=auth_headers,
        json={"current_password": "Shikshak2026", "new_password": "weakone"},
    )
    assert response.status_code == 422


def test_change_password_rejects_reusing_the_same_password(client, auth_headers):
    response = client.post(
        f"{API}/account/change-password",
        headers=auth_headers,
        json={"current_password": "Shikshak2026", "new_password": "Shikshak2026"},
    )
    assert response.status_code == 422
    assert "differ" in response.json()["detail"]


def test_change_password_works_and_invalidates_old_credentials(
    client, auth_headers, signup_payload
):
    response = client.post(
        f"{API}/account/change-password",
        headers=auth_headers,
        json={"current_password": "Shikshak2026", "new_password": "BrandNewPass9"},
    )
    assert response.status_code == 200

    # The old access token no longer works.
    assert client.get(f"{API}/account/profile", headers=auth_headers).status_code == 401

    assert (
        client.post(
            f"{API}/auth/login",
            json={"email": signup_payload["email"], "password": "Shikshak2026"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{API}/auth/login",
            json={"email": signup_payload["email"], "password": "BrandNewPass9"},
        ).status_code
        == 200
    )


def test_change_password_revokes_refresh_tokens(client, auth_headers, verified_user):
    client.post(
        f"{API}/account/change-password",
        headers=auth_headers,
        json={"current_password": "Shikshak2026", "new_password": "BrandNewPass9"},
    )
    response = client.post(
        f"{API}/auth/refresh", json={"refresh_token": verified_user["refresh_token"]}
    )
    assert response.status_code == 401


# --- Sessions --------------------------------------------------------------

def test_sessions_lists_active_sign_ins(client, auth_headers, signup_payload):
    client.post(
        f"{API}/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    sessions = client.get(f"{API}/account/sessions", headers=auth_headers).json()
    assert len(sessions) == 2
    assert all("expires_at" in s for s in sessions)


def test_revoking_one_session_leaves_the_others(client, auth_headers, signup_payload):
    client.post(
        f"{API}/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    sessions = client.get(f"{API}/account/sessions", headers=auth_headers).json()

    assert (
        client.delete(
            f"{API}/account/sessions/{sessions[0]['id']}", headers=auth_headers
        ).status_code
        == 200
    )
    remaining = client.get(f"{API}/account/sessions", headers=auth_headers).json()
    assert len(remaining) == 1


def test_cannot_revoke_a_session_you_do_not_own(client, auth_headers):
    response = client.delete(f"{API}/account/sessions/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


def test_revoke_all_signs_out_every_device(client, auth_headers, verified_user):
    assert (
        client.post(f"{API}/account/sessions/revoke-all", headers=auth_headers).status_code == 200
    )
    assert client.get(f"{API}/account/sessions", headers=auth_headers).json() == []
    assert (
        client.post(
            f"{API}/auth/refresh", json={"refresh_token": verified_user["refresh_token"]}
        ).status_code
        == 401
    )


# --- Deletion --------------------------------------------------------------

def test_delete_account_requires_the_password(client, auth_headers):
    response = client.request(
        "DELETE",
        f"{API}/account/",
        headers=auth_headers,
        json={"password": "WrongPass9", "confirm": "DELETE"},
    )
    assert response.status_code == 400


def test_delete_account_requires_the_confirmation_word(client, auth_headers):
    response = client.request(
        "DELETE",
        f"{API}/account/",
        headers=auth_headers,
        json={"password": "Shikshak2026", "confirm": "yes"},
    )
    assert response.status_code == 422


def test_delete_account_removes_the_user_and_their_lessons(client, auth_headers, db):
    client.post(f"{API}/lessons", headers=auth_headers, json={"topic": "Gravity"})
    assert db.scalars(select(Lesson)).all()

    response = client.request(
        "DELETE",
        f"{API}/account/",
        headers=auth_headers,
        json={"password": "Shikshak2026", "confirm": "DELETE"},
    )
    assert response.status_code == 200

    db.expire_all()
    assert db.scalars(select(User)).all() == []
    assert db.scalars(select(Lesson)).all() == [], "lessons must cascade with the account"
    assert db.scalars(select(RefreshToken)).all() == []


def test_deleted_account_cannot_sign_in(client, auth_headers, signup_payload):
    client.request(
        "DELETE",
        f"{API}/account/",
        headers=auth_headers,
        json={"password": "Shikshak2026", "confirm": "DELETE"},
    )
    response = client.post(
        f"{API}/auth/login",
        json={"email": signup_payload["email"], "password": signup_payload["password"]},
    )
    assert response.status_code == 401
