"""Offline tests for the agent-decision tracer (no LLM, no network, no DB)."""
import pytest

from modules.mlops.src.agent_trace import (
    ADAPTATION_DECIDED,
    PLAN_GENERATED,
    AgentTracer,
    tracer,
)


@pytest.fixture
def collected():
    """A tracer writing into a list instead of the database."""
    events = []
    local = AgentTracer()
    local.set_sink(events.append)
    return local, events


def test_event_carries_the_expected_envelope(collected):
    local, events = collected
    local.emit(PLAN_GENERATED, "lesson-1", node_id="n1", node_count=3)

    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == PLAN_GENERATED
    assert event["session_id"] == "lesson-1"
    assert event["node_id"] == "n1"
    assert event["payload"] == {"node_count": 3}
    assert event["occurred_at"].endswith("+00:00")


def test_prompts_and_raw_content_never_reach_the_sink(collected):
    """A trace is shown to humans, so it must not carry prompts or answers."""
    local, events = collected
    local.emit(
        PLAN_GENERATED,
        "lesson-1",
        prompt="you are a teacher...",
        system_prompt="...",
        script_text="the full narration",
        raw_answer="1/6",
        reasoning="chain of thought",
        api_key="secret",
        node_count=2,
    )

    payload = events[0]["payload"]
    assert payload == {"node_count": 2}


def test_long_values_are_truncated_not_stored_whole(collected):
    local, events = collected
    local.emit(ADAPTATION_DECIDED, "lesson-1", reason="x" * 900)

    reason = events[0]["payload"]["reason"]
    assert len(reason) < 400
    assert reason.endswith("…")


def test_a_failing_sink_never_breaks_the_caller(collected):
    local, _ = collected

    def explode(_event):
        raise RuntimeError("database is down")

    local.set_sink(explode)
    # Must return normally: tracing is never allowed to interrupt teaching.
    event = local.emit(PLAN_GENERATED, "lesson-1", node_count=1)
    assert event["event_type"] == PLAN_GENERATED


def test_events_without_a_session_are_not_persisted(collected):
    local, events = collected
    local.emit(PLAN_GENERATED, None, node_count=1)
    assert events == []


def test_disabling_the_tracer_stops_persistence(collected):
    local, events = collected
    local.set_enabled(False)
    local.emit(PLAN_GENERATED, "lesson-1", node_count=1)
    assert events == []
    local.set_enabled(True)


def test_module_singleton_is_safe_without_a_sink():
    """Producers import the global tracer; with no backend it must no-op."""
    assert tracer.emit(PLAN_GENERATED, "lesson-x", node_count=1)["session_id"] == "lesson-x"
