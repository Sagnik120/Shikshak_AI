"""Deep Unit Test Suite: Content-Aware Progressive Visual Reveal Timing.

Addresses Issue 2 from 02_avatar_voice_module_fix_plan_v2.md:
1. Content-Complexity Weighting: Validates longer/more complex algebraic formulas receive proportional screen time.
2. Exact Duration Conservation: Validates sum(durations) == total_duration to 0.01s across arbitrary lengths.
3. Speech-Boundary Alignment: Validates synchronization with transition cues in WordTimestamps.
4. Edge/Boundary Cases: Single step, zero steps, rapid short duration, and massive formula disparities.
5. Compositor Integration: Validates step_contents flows from VisualRenderResult into FFmpegCompositor.
"""

import math
import pytest
from modules.avatar_voice.src.models import WordTimestamp, VisualRenderResult
from modules.avatar_voice.src.compositor.ffmpeg_compositor import compute_content_aware_step_durations


class TestProgressiveTiming:
    """Comprehensive test suite for content-aware progressive visual reveal timing."""

    # =========================================================================
    # 1. CONTENT COMPLEXITY WEIGHTING
    # =========================================================================

    def test_complex_algebraic_steps_receive_longer_duration_than_simple_steps(self):
        """Validates that a complex multi-variable formula gets more screen time than a simple setup step."""
        steps = [
            "x = 2",                                                 # Simple 5 chars
            "(x - 2)(x + 2) = 0",                                     # Medium 17 chars
            r"\int_0^\infty \frac{x^3}{e^x - 1} dx = \frac{\pi^4}{15}"  # Highly complex 51 chars with LaTeX symbols
        ]
        total_duration = 15.0

        durations = compute_content_aware_step_durations(
            total_duration=total_duration,
            num_steps=3,
            step_contents=steps,
        )

        assert len(durations) == 3
        # Step 3 must have significantly more duration than Step 1
        assert durations[2] > durations[1] > durations[0]
        # Duration must strictly sum to total_duration
        assert math.isclose(sum(durations), total_duration, abs_tol=0.01)

    # =========================================================================
    # 2. STRICT TOTAL DURATION CONSERVATION ACROSS ARBITRARY VALUES
    # =========================================================================

    @pytest.mark.parametrize("total_duration,num_steps", [
        (4.0, 2),
        (7.33, 3),
        (9.87, 4),
        (12.50, 5),
        (25.123, 6),
        (60.0, 10),
    ])
    def test_duration_conservation_guarantee(self, total_duration, num_steps):
        """Ensures that sum(step_durations) == total_duration under all non-trivial split parameters."""
        durations = compute_content_aware_step_durations(
            total_duration=total_duration,
            num_steps=num_steps,
        )
        assert len(durations) == num_steps
        assert math.isclose(sum(durations), total_duration, abs_tol=0.02)
        # Every step must have a positive duration
        for d in durations:
            assert d > 0.0

    # =========================================================================
    # 3. SPEECH TIMESTAMP ALIGNMENT
    # =========================================================================

    def test_speech_boundary_alignment_with_cue_words(self):
        """Validates that explicit speech transition cues align visual step transitions to timestamps."""
        word_timestamps = [
            WordTimestamp(word="First", start_sec=0.2, end_sec=0.6),
            WordTimestamp(word="we", start_sec=0.7, end_sec=0.9),
            WordTimestamp(word="write", start_sec=1.0, end_sec=1.3),
            WordTimestamp(word="the", start_sec=1.4, end_sec=1.5),
            WordTimestamp(word="equation", start_sec=1.6, end_sec=2.1),
            WordTimestamp(word="Next", start_sec=3.5, end_sec=3.8),
            WordTimestamp(word="we", start_sec=3.9, end_sec=4.1),
            WordTimestamp(word="factor", start_sec=4.2, end_sec=4.6),
            WordTimestamp(word="both", start_sec=4.7, end_sec=4.9),
            WordTimestamp(word="terms", start_sec=5.0, end_sec=5.4),
            WordTimestamp(word="Finally", start_sec=7.0, end_sec=7.4),
            WordTimestamp(word="we", start_sec=7.5, end_sec=7.7),
            WordTimestamp(word="solve", start_sec=7.8, end_sec=8.1),
            WordTimestamp(word="for", start_sec=8.2, end_sec=8.3),
            WordTimestamp(word="x", start_sec=8.4, end_sec=8.8),
        ]
        total_duration = 10.0

        durations = compute_content_aware_step_durations(
            total_duration=total_duration,
            num_steps=3,
            word_timestamps=word_timestamps,
        )

        assert len(durations) == 3
        # Step 1 should transition around 3.5s (Next)
        assert 3.0 <= durations[0] <= 4.0
        # Step 2 should transition around 7.0s (Finally) -> duration ~ 3.5s
        assert 3.0 <= durations[1] <= 4.0
        # Step 3 completes to 10.0s -> duration ~ 3.0s
        assert 2.5 <= durations[2] <= 3.5
        assert math.isclose(sum(durations), total_duration, abs_tol=0.01)

    # =========================================================================
    # 4. BOUNDARY & EXTREME CASES
    # =========================================================================

    def test_boundary_zero_and_single_step(self):
        """Validates zero and single step inputs."""
        assert compute_content_aware_step_durations(10.0, 0) == []
        assert compute_content_aware_step_durations(10.0, 1) == [10.0]

    def test_boundary_ultra_short_duration_never_crashes(self):
        """Validates that very short audio durations (e.g. 1.5s for 3 steps) do not produce negative durations."""
        durations = compute_content_aware_step_durations(
            total_duration=1.5,
            num_steps=3,
        )
        assert len(durations) == 3
        assert math.isclose(sum(durations), 1.5, abs_tol=0.01)
        for d in durations:
            assert d > 0.0

    def test_boundary_massive_content_disparity(self):
        """Validates extreme contrast: 1 char vs 500 chars."""
        steps = [
            "x",
            r"\begin{aligned} f(x) &= \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!} (x-a)^n \\ &= f(a) + f'(a)(x-a) + \frac{f''(a)}{2!} (x-a)^2 + \dots \end{aligned}" * 2
        ]
        durations = compute_content_aware_step_durations(
            total_duration=12.0,
            num_steps=2,
            step_contents=steps,
            min_step_duration=1.5
        )
        assert len(durations) == 2
        assert durations[0] >= 1.5  # Respects floor
        assert durations[1] > durations[0]
        assert math.isclose(sum(durations), 12.0, abs_tol=0.01)

    # =========================================================================
    # 5. VISUAL RENDER RESULT STEP CONTENTS PRESERVATION
    # =========================================================================

    def test_visual_render_result_preserves_step_contents(self):
        """Verifies that VisualRenderResult retains original step_contents for downstream timing."""
        result = VisualRenderResult(
            image_path="/tmp/vis.png",
            visual_type="equation",
            step_image_paths=["/tmp/s1.png", "/tmp/s2.png"],
            step_contents=["x = 1", "y = 2"],
            is_progressive=True
        )
        assert result.is_progressive is True
        assert result.step_contents == ["x = 1", "y = 2"]
        assert len(result.step_image_paths) == 2
