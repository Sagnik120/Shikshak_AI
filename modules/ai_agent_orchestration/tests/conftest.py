import pytest

from modules.ai_agent_orchestration.src.adapters import gemini_adapter


@pytest.fixture(autouse=True)
def _no_gemini_cooldown():
    """A simulated outage in one test must not skip another test's call."""
    gemini_adapter._cooldown["until"] = 0.0
    yield
    gemini_adapter._cooldown["until"] = 0.0
