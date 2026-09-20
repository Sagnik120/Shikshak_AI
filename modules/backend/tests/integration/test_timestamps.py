"""Timestamps must survive the SQLite round trip as unambiguous UTC.

SQLite has no timestamp type. Without an explicit UTC-aware column type, values
come back naive, serialise without an offset, and every browser reads them as
local time — so a lesson created seconds ago renders as hours old.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from modules.backend.src.db.models import Document, Lesson, User

API = "/api/v1"


def test_stored_timestamps_come_back_timezone_aware(client, auth_headers, db):
    client.post(f"{API}/lessons", headers=auth_headers, json={"topic": "Gravity"})

    lesson = db.scalars(select(Lesson)).first()
    assert lesson.created_at.tzinfo is not None
    assert lesson.updated_at.tzinfo is not None


def test_stored_timestamps_are_actually_now(client, auth_headers, db):
    """The classic symptom of the bug: a fresh row looks hours old."""
    client.post(f"{API}/lessons", headers=auth_headers, json={"topic": "Gravity"})

    lesson = db.scalars(select(Lesson)).first()
    age = datetime.now(timezone.utc) - lesson.created_at
    assert abs(age) < timedelta(minutes=1), f"a just-created lesson is dated {age} ago"


def test_api_timestamps_carry_an_offset(client, auth_headers):
    """Without an offset a browser parses the value in its own timezone."""
    created = client.post(f"{API}/lessons", headers=auth_headers, json={"topic": "Gravity"})
    lesson_id = created.json()["lesson_id"]

    detail = client.get(f"{API}/lessons/{lesson_id}", headers=auth_headers).json()
    for field in ("created_at", "updated_at"):
        value = detail[field]
        assert value.endswith("+00:00") or value.endswith("Z"), f"{field} has no offset: {value}"
        # And it must parse back to roughly now.
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        assert abs(datetime.now(timezone.utc) - parsed) < timedelta(minutes=1)


def test_document_timestamps_carry_an_offset(client, auth_headers):
    upload = client.post(
        f"{API}/lessons/documents",
        headers=auth_headers,
        files={"file": ("notes.txt", b"Gravity pulls objects toward the Earth's centre.", "text/plain")},
    )
    assert upload.status_code == 201

    listed = client.get(f"{API}/lessons/documents", headers=auth_headers).json()
    value = listed[0]["created_at"]
    assert value.endswith("+00:00") or value.endswith("Z"), value


def test_user_timestamps_carry_an_offset(client, auth_headers):
    profile = client.get(f"{API}/account/profile", headers=auth_headers).json()
    for field in ("created_at", "last_login_at"):
        value = profile.get(field)
        if value:
            assert "+" in value[10:] or value.endswith("Z"), f"{field} has no offset: {value}"


def test_session_expiry_is_in_the_future(client, auth_headers):
    """A naive expiry read as local time can look already expired."""
    sessions = client.get(f"{API}/account/sessions", headers=auth_headers).json()
    assert sessions

    expires = datetime.fromisoformat(sessions[0]["expires_at"].replace("Z", "+00:00"))
    assert expires > datetime.now(timezone.utc)
