"""Agent traces: emitted by mlops, persisted into lesson_events, read back over the API."""
import pytest

from modules.backend.src.services import agent_trace_sink
from modules.mlops.src.agent_trace import (
    ADAPTATION_DECIDED,
    PLAN_GENERATED,
    RETRIEVAL_ATTEMPT,
    RETRIEVAL_RESOLVED,
    tracer,
)


@pytest.fixture
def sink_installed():
    """Install the real DB sink for the test, then restore the previous state."""
    agent_trace_sink.install()
    yield
    tracer.set_sink(None)


@pytest.fixture
def lesson(client, auth_headers):
    response = client.post(
        "/api/v1/lessons",
        json={"topic": "Newton's Laws", "level": "beginner", "language": "en", "time_budget_min": 5},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["lesson_id"]


def test_emitted_events_are_persisted_and_readable(client, auth_headers, lesson, sink_installed):
    tracer.emit(PLAN_GENERATED, lesson, node_count=2, used_learner_memory=False)
    tracer.emit(RETRIEVAL_ATTEMPT, lesson, node_id="n1", attempt=1, has_sufficient_context=False)
    tracer.emit(RETRIEVAL_ATTEMPT, lesson, node_id="n1", attempt=2, has_sufficient_context=True)
    tracer.emit(RETRIEVAL_RESOLVED, lesson, node_id="n1", attempts=2, was_refined=True)
    tracer.emit(ADAPTATION_DECIDED, lesson, node_id="n1", action="MODIFY", reason="misconception")

    response = client.get(f"/api/v1/lessons/{lesson}/trace", headers=auth_headers)
    assert response.status_code == 200

    events = response.json()["events"]
    assert [e["event_type"] for e in events] == [
        PLAN_GENERATED,
        RETRIEVAL_ATTEMPT,
        RETRIEVAL_ATTEMPT,
        RETRIEVAL_RESOLVED,
        ADAPTATION_DECIDED,
    ]
    # The refinement loop is visible end to end — this is Demo 1 of the plan.
    assert events[1]["payload"]["has_sufficient_context"] is False
    assert events[3]["payload"]["was_refined"] is True
    assert events[4]["payload"]["action"] == "MODIFY"


def test_lifecycle_events_are_not_mixed_into_the_agent_trace(
    client, auth_headers, lesson, sink_installed
):
    """`lesson_created` and friends share the table but are not agent decisions."""
    tracer.emit(PLAN_GENERATED, lesson, node_count=1)

    events = client.get(f"/api/v1/lessons/{lesson}/trace", headers=auth_headers).json()["events"]

    assert all(e["event_type"].startswith("agent.") for e in events)
    assert not any(e["event_type"] == "lesson_created" for e in events)


def test_traces_never_expose_prompts_even_if_a_caller_passes_them(
    client, auth_headers, lesson, sink_installed
):
    tracer.emit(
        PLAN_GENERATED,
        lesson,
        prompt="You are an expert teacher...",
        script_text="full narration text",
        node_count=1,
    )

    payload = client.get(f"/api/v1/lessons/{lesson}/trace", headers=auth_headers).json()["events"][0][
        "payload"
    ]
    assert payload == {"node_count": 1}


def test_another_learner_cannot_read_this_trace(client, auth_headers, lesson, sink_installed):
    tracer.emit(PLAN_GENERATED, lesson, node_count=1)

    signup = client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Other Learner", "email": "other@example.com", "password": "Shikshak2026"},
    )
    client.post(
        "/api/v1/auth/verify-email",
        json={"email": "other@example.com", "code": signup.json()["dev_otp"]},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": "other@example.com", "password": "Shikshak2026"}
    ).json()

    response = client.get(
        f"/api/v1/lessons/{lesson}/trace",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 404


def test_trace_requires_authentication(client, lesson):
    assert client.get(f"/api/v1/lessons/{lesson}/trace").status_code == 401


def test_events_for_an_unknown_session_are_dropped_not_written(client, auth_headers, sink_installed):
    """A trace whose session isn't a persisted lesson must not break anything."""
    tracer.emit(PLAN_GENERATED, "not-a-real-lesson-id", node_count=1)  # must not raise
