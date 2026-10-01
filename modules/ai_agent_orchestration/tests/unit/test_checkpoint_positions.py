"""Mid-video checkpoints land at sentence ends, strictly inside the script."""
from modules.ai_agent_orchestration.src.state_machine.orchestrator import TeacherOrchestrator

SENTENCE = "Water evaporates from the sea and rises into the sky as vapour. "


def _ends(script: str) -> set:
    total, ends = 0, set()
    for s in script.strip().split(". "):
        total += len(s.split())
        ends.add(total)
    return ends


def test_short_script_gets_one_question_in_the_middle():
    script = SENTENCE * 8  # ~96 words
    positions = TeacherOrchestrator.checkpoint_positions(script)
    total = len(script.split())
    assert len(positions) == 1
    assert 0 < positions[0] < total


def test_long_script_gets_several_questions_spread_through_it():
    script = SENTENCE * 45  # ~540 words
    positions = TeacherOrchestrator.checkpoint_positions(script)
    total = len(script.split())
    assert 2 <= len(positions) <= 3
    assert positions == sorted(positions)
    assert all(0 < p < total for p in positions)
    assert set(positions) <= _ends(script)


def test_empty_script_has_no_checkpoints():
    assert TeacherOrchestrator.checkpoint_positions("") == []
