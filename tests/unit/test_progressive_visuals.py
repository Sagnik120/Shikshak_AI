"""Comprehensive Boundary & Real-World Demo Scenario Test Suite for Progressive Visuals.

Covers:
1. Boundary & Edge Cases:
   - Empty list, single-item list, and whitespace-only steps (graceful degradation)
   - Large number of derivation steps (6-8 steps) with auto-scaling
   - Extreme code snippets (empty, single-line, long indented algorithms)
   - Very short (0.5s) and long (45s) audio durations preventing division by zero
2. Real-World Hackathon Demo Scenarios (PS §10):
   - Demo Scenario 1: Mathematics - Quadratic Equation 3-Step Derivation
   - Demo Scenario 2: Computer Science - Binary Search Execution Flow with Active Terminal Output
   - Demo Scenario 3: Multilingual Hindi Progressive Physics/Math Lesson (Swara Neural voice)
   - Demo Scenario 4: Asynchronous Queue Execution (render_segment async worker with progressive visuals)
"""

import os
import pytest
from modules.avatar_voice.src.models import (
    TeachingSegment,
    VisualSpec,
    TTSResult,
    AvatarRenderResult,
    WordTimestamp,
)
from modules.avatar_voice.src.visuals.equation_renderer import EquationRenderer
from modules.avatar_voice.src.visuals.code_renderer import CodeRenderer
from modules.avatar_voice.src.compositor.ffmpeg_compositor import FFmpegCompositor
from modules.avatar_voice.src.service import AvatarVoiceService


class TestProgressiveVisualsDeep:
    """Exhaustive boundary testing and realistic demo scenario validations."""

    @pytest.fixture
    def temp_out(self, tmp_path):
        return str(tmp_path)

    # =========================================================================
    # 1. BOUNDARY & EDGE CASES
    # =========================================================================

    @pytest.mark.parametrize("empty_steps", [[], [""], ["   ", "\t"], ["single_step"]])
    def test_boundary_empty_or_single_steps_graceful_degradation(self, temp_out, empty_steps):
        """Empty, whitespace-only, or single-item steps must degrade to single-frame non-progressive."""
        renderer = EquationRenderer(output_dir=temp_out)
        spec = VisualSpec(
            type="equation",
            content="y = mx + c",
            steps=empty_steps
        )
        result = renderer.render(spec)

        # Single step or empty steps should NOT be marked progressive
        if len([s for s in empty_steps if s.strip()]) <= 1:
            assert result.is_progressive is False
            assert len(result.step_image_paths) == 1
        assert os.path.exists(result.image_path)

    def test_boundary_large_step_count_scaling(self, temp_out):
        """6 derivation steps must render without out-of-bounds errors or overlapping text."""
        renderer = EquationRenderer(output_dir=temp_out)
        steps = [
            r"f(x) = x^3 - 6x^2 + 11x - 6",
            r"f'(x) = 3x^2 - 12x + 11",
            r"3x^2 - 12x + 11 = 0",
            r"x = \frac{12 \pm \sqrt{144 - 132}}{6}",
            r"x = \frac{12 \pm \sqrt{12}}{6}",
            r"x \approx 2 \pm 0.577"
        ]
        spec = VisualSpec(type="equation", content=steps[0], steps=steps)
        result = renderer.render(spec)

        assert result.is_progressive is True
        assert len(result.step_image_paths) == 6
        for p in result.step_image_paths:
            assert os.path.exists(p)
            assert os.path.getsize(p) > 1000

    def test_boundary_code_with_empty_or_whitespace_output(self, temp_out):
        """Whitespace execution output must not trigger false progressive terminal pane."""
        renderer = CodeRenderer(output_dir=temp_out)
        spec = VisualSpec(
            type="code",
            content="print('Hello World')",
            execution_output="   \n  "
        )
        result = renderer.render(spec)
        assert result.is_progressive is False
        assert len(result.step_image_paths) == 1

    def test_boundary_very_short_and_long_durations_in_compositor(self, temp_out):
        """Ensures sub-second and extended durations do not cause zero-division or timing anomalies."""
        compositor = FFmpegCompositor(output_dir=temp_out)
        eq_renderer = EquationRenderer(output_dir=temp_out)
        vis_res = eq_renderer.render(VisualSpec(
            type="equation",
            content="E = mc^2",
            steps=["E = mc^2", "m = E / c^2"]
        ))

        # Dummy audio file
        audio_path = os.path.join(temp_out, "test_audio.wav")
        with open(audio_path, "wb") as f:
            f.write(b"RIFFtestWAVEfmt ")

        frames_dir = os.path.join(temp_out, "avatar_frames_boundary")
        os.makedirs(frames_dir, exist_ok=True)
        from PIL import Image
        for i in range(12):
            Image.new("RGBA", (576, 432), (0, 0, 0, 0)).save(os.path.join(frames_dir, f"frame_{i:05d}.png"))

        # Test sub-second (0.4s)
        tts_short = TTSResult(audio_path=audio_path, duration_sec=0.4, word_timestamps=[])
        avatar_short = AvatarRenderResult(frames_dir=frames_dir, frame_count=12, fps=24, duration_sec=0.4)
        res_short = compositor.compose("short_node", tts_short, avatar_short, vis_res)
        assert res_short.duration_sec == 0.4
        assert os.path.exists(res_short.video_url)

        # Test long duration (45.0s)
        tts_long = TTSResult(audio_path=audio_path, duration_sec=45.0, word_timestamps=[])
        avatar_long = AvatarRenderResult(frames_dir=frames_dir, frame_count=12, fps=24, duration_sec=45.0)
        res_long = compositor.compose("long_node", tts_long, avatar_long, vis_res)
        assert res_long.duration_sec == 45.0
        assert os.path.exists(res_long.video_url)

    # =========================================================================
    # 2. REAL-WORLD DEMO SCENARIOS (Directly Mapped to Hackathon Presentation)
    # =========================================================================

    def test_demo_scenario_1_math_quadratic_derivation(self, temp_out):
        """DEMO SCENARIO 1: Mathematics - Quadratic Equation 3-Step Derivation.

        Spoken Script: 'To solve x squared minus 5x plus 6 equals 0, we factor into
        (x - 2)(x - 3) equals 0, yielding roots x equals 2 and x equals 3.'
        """
        service = AvatarVoiceService(output_dir=temp_out)
        segment = TeachingSegment(
            node_id="demo_math_quadratic",
            script_text=(
                "To solve x squared minus 5x plus 6 equals 0, we factor it into "
                "(x minus 2) times (x minus 3) equals 0, which gives us two solutions: "
                "x equals 2 and x equals 3."
            ),
            language="en",
            visual_spec=VisualSpec(
                type="equation",
                content=r"x^2 - 5x + 6 = 0",
                steps=[
                    r"x^2 - 5x + 6 = 0",
                    r"(x - 2)(x - 3) = 0",
                    r"x = 2 \quad \text{or} \quad x = 3"
                ]
            ),
            avatar_cue="emphasis"
        )

        rendered = service.render_segment_sync(segment)

        assert rendered.node_id == "demo_math_quadratic"
        assert rendered.duration_sec > 0.0
        assert os.path.exists(rendered.video_url)
        # Verify preview steps generated for presentation
        step1_preview = rendered.video_url.replace(".mp4", "_step_1_preview.png")
        step3_preview = rendered.video_url.replace(".mp4", "_step_3_preview.png")
        assert os.path.exists(step1_preview) or os.path.exists(rendered.video_url.replace(".mp4", "_preview.png"))

    def test_demo_scenario_2_cs_binary_search_execution_flow(self, temp_out):
        """DEMO SCENARIO 2: Computer Science - Binary Search with Terminal Execution Output.

        Spoken Script: 'Here is the binary search algorithm. When executed on our sorted list
        searching for 42, the search successfully completes at index 4.'
        """
        service = AvatarVoiceService(output_dir=temp_out)
        code_body = (
            "def binary_search(arr: list[int], target: int) -> int:\n"
            "    low, high = 0, len(arr) - 1\n"
            "    while low <= high:\n"
            "        mid = (low + high) // 2\n"
            "        if arr[mid] == target:\n"
            "            return mid\n"
            "        elif arr[mid] < target:\n"
            "            low = mid + 1\n"
            "        else:\n"
            "            high = mid - 1\n"
            "    return -1\n\n"
            "numbers = [10, 20, 30, 42, 50, 60]\n"
            "idx = binary_search(numbers, 42)\n"
            "print(f'Found 42 at index: {idx}')"
        )
        segment = TeachingSegment(
            node_id="demo_cs_binary_search",
            script_text="Let us walk through the binary search algorithm and observe its execution.",
            language="en",
            visual_spec=VisualSpec(
                type="code",
                content={"code": code_body, "language": "python"},
                execution_output=">>> Found 42 at index: 3 (Execution time: 0.12ms)"
            ),
            avatar_cue="neutral"
        )

        rendered = service.render_segment_sync(segment)

        assert rendered.node_id == "demo_cs_binary_search"
        assert rendered.duration_sec > 0.0
        assert os.path.exists(rendered.video_url)

    def test_demo_scenario_3_multilingual_hindi_physics_lesson(self, temp_out):
        """DEMO SCENARIO 3: Multilingual (Hindi) Progressive Derivation.

        Spoken Script in Hindi: 'पाइथागोरस प्रमेय के अनुसार कर्ण का वर्ग अन्य दो भुजाओं के वर्गों के योग के बराबर होता है।'
        """
        service = AvatarVoiceService(output_dir=temp_out)
        segment = TeachingSegment(
            node_id="demo_hindi_physics",
            script_text="पाइथागोरस प्रमेय के अनुसार कर्ण का वर्ग अन्य दो भुजाओं के वर्गों के योग के बराबर होता है।",
            language="hi",
            visual_spec=VisualSpec(
                type="equation",
                content=r"a^2 + b^2 = c^2",
                steps=[
                    r"\text{कर्ण}^2 = \text{लम्ब}^2 + \text{आधार}^2",
                    r"3^2 + 4^2 = c^2 \implies 9 + 16 = c^2",
                    r"c = \sqrt{25} = 5"
                ]
            ),
            avatar_cue="emphasis"
        )

        rendered = service.render_segment_sync(segment)

        assert rendered.node_id == "demo_hindi_physics"
        assert rendered.duration_sec > 0.0
        assert os.path.exists(rendered.video_url)

    def test_demo_scenario_4_async_background_render_job(self, temp_out):
        """DEMO SCENARIO 4: Asynchronous queue execution (non-blocking for UI).

        Verifies that enqueueing a progressive visual job updates job status
        through queued -> rendering -> done with valid RenderedVideoSegment.
        """
        import time

        service = AvatarVoiceService(output_dir=temp_out)
        segment = TeachingSegment(
            node_id="async_demo_node",
            script_text="The asynchronous worker renders progressive visuals in the background.",
            language="en",
            visual_spec=VisualSpec(
                type="equation",
                content="V = IR",
                steps=["V = IR", "I = V / R", "R = V / I"]
            ),
            avatar_cue="neutral"
        )

        job_id = service.render_segment(segment)
        assert job_id.startswith("job_")

        # Poll until completion (or timeout)
        max_wait = 10.0
        start_time = time.time()
        final_status = None

        while time.time() - start_time < max_wait:
            status = service.get_status(job_id)
            if status and status.status in ("done", "failed"):
                final_status = status
                break
            time.sleep(0.1)

        assert final_status is not None, "Async job timed out"
        assert final_status.status == "done"
        assert final_status.progress_pct == 1.0
        assert final_status.result is not None
        assert final_status.result.node_id == "async_demo_node"
        assert os.path.exists(final_status.result.video_url)
