"""Lesson lifecycle, tenant isolation, and media access control."""
import pytest
from sqlalchemy import select

from modules.backend.src.db.models import Lesson, LessonNodeRow, User

API = "/api/v1"

PLAN_FIXTURE = {
    "lesson_id": "plan-fixture-1",
    "source": "topic",
    "constraints": {"level": "beginner", "language": "en", "time_budget_min": 10},
    "nodes": [
        {
            "node_id": "node-1",
            "concept": "What a force is",
            "depth": "intro",
            "est_minutes": 3,
            "visual_type": "diagram",
            "checkpoint_question": True,
        },
        {
            "node_id": "node-2",
            "concept": "Newton's second law",
            "depth": "core",
            "est_minutes": 4,
            "visual_type": "equation",
            "checkpoint_question": True,
        },
    ],
}


@pytest.fixture
def second_user(client):
    """A second verified account, used to prove data never crosses accounts."""
    signup = client.post(
        f"{API}/auth/signup",
        json={
            "full_name": "Other Learner",
            "email": "other@example.com",
            "password": "OtherPass2026",
        },
    )
    verified = client.post(
        f"{API}/auth/verify-email",
        json={"email": "other@example.com", "code": signup.json()["dev_otp"]},
    )
    return {"Authorization": f"Bearer {verified.json()['access_token']}"}


@pytest.fixture
def planned_lesson(client, auth_headers, db, monkeypatch):
    """A lesson with a plan persisted, without calling the live LLM."""
    from modules.backend.src.services.session_manager import session_manager

    created = client.post(
        f"{API}/lessons",
        headers=auth_headers,
        json={"topic": "Newton's Laws", "level": "beginner", "time_budget_min": 10},
    )
    lesson_id = created.json()["lesson_id"]

    from modules.ai_agent_orchestration.src.schemas.lesson import LessonPlan

    monkeypatch.setattr(
        session_manager, "build_plan", lambda lesson, db=None: LessonPlan(**PLAN_FIXTURE)
    )
    response = client.post(f"{API}/lessons/{lesson_id}/plan", headers=auth_headers)
    assert response.status_code == 200, response.text
    return lesson_id


def test_create_lesson_requires_topic_or_document(client, auth_headers):
    response = client.post(f"{API}/lessons", headers=auth_headers, json={})
    assert response.status_code == 422
    assert "topic" in response.json()["detail"].lower()


def test_create_lesson_persists_constraints(client, auth_headers, db):
    response = client.post(
        f"{API}/lessons",
        headers=auth_headers,
        json={
            "topic": "Photosynthesis",
            "level": "advanced",
            "language": "hi",
            "time_budget_min": 25,
        },
    )
    assert response.status_code == 201

    lesson = db.get(Lesson, response.json()["lesson_id"])
    assert lesson.level == "advanced"
    assert lesson.language == "hi"
    assert lesson.time_budget_min == 25
    assert lesson.status == "created"


def test_create_lesson_rejects_an_invalid_level(client, auth_headers):
    response = client.post(
        f"{API}/lessons", headers=auth_headers, json={"topic": "X", "level": "expert"}
    )
    assert response.status_code == 422


def test_plan_persists_every_node(client, auth_headers, planned_lesson, db):
    nodes = db.scalars(
        select(LessonNodeRow).where(LessonNodeRow.lesson_id == planned_lesson)
    ).all()
    assert len(nodes) == 2
    assert {n.node_id for n in nodes} == {"node-1", "node-2"}
    assert all(n.status == "pending" for n in nodes)
    assert db.get(Lesson, planned_lesson).status == "planned"


def test_lesson_detail_exposes_nodes_and_progress(client, auth_headers, planned_lesson):
    detail = client.get(f"{API}/lessons/{planned_lesson}", headers=auth_headers).json()
    assert detail["node_count"] == 2
    assert detail["progress_pct"] == 0.0
    assert detail["nodes"][0]["concept"] == "What a force is"
    assert detail["report"] is None


def test_lesson_list_supports_search_and_status_filters(client, auth_headers, planned_lesson):
    client.post(f"{API}/lessons", headers=auth_headers, json={"topic": "Photosynthesis"})

    all_lessons = client.get(f"{API}/lessons", headers=auth_headers).json()
    assert all_lessons["total"] == 2

    searched = client.get(f"{API}/lessons?search=photo", headers=auth_headers).json()
    assert searched["total"] == 1
    assert "Photosynthesis" in searched["lessons"][0]["title"]

    filtered = client.get(f"{API}/lessons?status=planned", headers=auth_headers).json()
    assert filtered["total"] == 1


def test_delete_lesson_removes_it(client, auth_headers, planned_lesson):
    assert client.delete(f"{API}/lessons/{planned_lesson}", headers=auth_headers).status_code == 200
    assert client.get(f"{API}/lessons/{planned_lesson}", headers=auth_headers).status_code == 404


# --- Tenant isolation ------------------------------------------------------

def test_another_user_cannot_read_your_lesson(client, planned_lesson, second_user):
    assert client.get(f"{API}/lessons/{planned_lesson}", headers=second_user).status_code == 404


def test_another_user_cannot_delete_your_lesson(client, planned_lesson, second_user):
    assert client.delete(f"{API}/lessons/{planned_lesson}", headers=second_user).status_code == 404


def test_another_user_cannot_plan_your_lesson(client, planned_lesson, second_user):
    assert (
        client.post(f"{API}/lessons/{planned_lesson}/plan", headers=second_user).status_code == 404
    )


def test_another_user_cannot_get_a_ticket_for_your_lesson(client, planned_lesson, second_user):
    assert (
        client.post(f"{API}/lessons/{planned_lesson}/ticket", headers=second_user).status_code
        == 404
    )


def test_lesson_lists_are_scoped_per_account(client, auth_headers, planned_lesson, second_user):
    assert client.get(f"{API}/lessons", headers=second_user).json()["total"] == 0
    assert client.get(f"{API}/lessons", headers=auth_headers).json()["total"] == 1


# --- Media access control --------------------------------------------------

def test_video_endpoint_requires_authentication(client, planned_lesson):
    assert client.get(f"{API}/lessons/{planned_lesson}/nodes/node-1/video").status_code == 401


def test_video_endpoint_404s_before_a_render_exists(client, auth_headers, planned_lesson):
    response = client.get(
        f"{API}/lessons/{planned_lesson}/nodes/node-1/video", headers=auth_headers
    )
    assert response.status_code == 404


def test_media_cannot_escape_the_lesson_directory(client, auth_headers, planned_lesson, db):
    """A stored path outside the lesson's media dir must never be served.

    The previous endpoint took a raw filesystem path from the query string,
    which served any file the process could read.
    """
    node = db.scalars(
        select(LessonNodeRow).where(
            LessonNodeRow.lesson_id == planned_lesson, LessonNodeRow.node_id == "node-1"
        )
    ).first()
    node.video_path = "/etc/passwd"
    db.commit()

    response = client.get(
        f"{API}/lessons/{planned_lesson}/nodes/node-1/video", headers=auth_headers
    )
    assert response.status_code == 404


# --- Documents -------------------------------------------------------------

def test_upload_rejects_an_unsupported_extension(client, auth_headers):
    response = client.post(
        f"{API}/lessons/documents",
        headers=auth_headers,
        files={"file": ("notes.exe", b"binary", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_upload_rejects_an_empty_file(client, auth_headers):
    response = client.post(
        f"{API}/lessons/documents",
        headers=auth_headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 422


def test_uploaded_text_document_is_ingested_and_listed(client, auth_headers):
    content = (
        b"Chapter 1: Photosynthesis\n\n"
        b"Photosynthesis is the process by which green plants use sunlight to "
        b"synthesise food from carbon dioxide and water. Chlorophyll in the "
        b"chloroplasts absorbs light energy. The products are glucose and oxygen.\n\n"
        b"Chapter 2: Respiration\n\n"
        b"Respiration releases energy from glucose inside the mitochondria.\n"
    )
    response = client.post(
        f"{API}/lessons/documents",
        headers=auth_headers,
        files={"file": ("biology.txt", content, "text/plain")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "ready"
    assert body["chunk_count"] > 0

    listed = client.get(f"{API}/lessons/documents", headers=auth_headers).json()
    assert len(listed) == 1
    assert listed[0]["filename"] == "biology.txt"


def test_documents_are_scoped_per_account(client, auth_headers, second_user):
    client.post(
        f"{API}/lessons/documents",
        headers=auth_headers,
        files={"file": ("mine.txt", b"Some study material about gravity and mass.", "text/plain")},
    )
    assert client.get(f"{API}/lessons/documents", headers=second_user).json() == []


def test_cannot_build_a_lesson_on_someone_elses_document(client, auth_headers, second_user):
    upload = client.post(
        f"{API}/lessons/documents",
        headers=auth_headers,
        files={"file": ("mine.txt", b"Some study material about gravity and mass.", "text/plain")},
    )
    document_id = upload.json()["document_id"]

    response = client.post(
        f"{API}/lessons", headers=second_user, json={"document_id": document_id}
    )
    assert response.status_code == 404
