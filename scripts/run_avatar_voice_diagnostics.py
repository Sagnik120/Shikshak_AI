"""
Diagnostic & Verification Suite for avatar_voice Module.
Runs comprehensive checks across TTS, Viseme Avatar, Visual Renderers, Compositor, and Async Service.
"""

import os
import sys
import time
from typing import Callable, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules.avatar_voice.src import (
    AvatarVoiceService,
    FallbackTTSAdapter,
    TeachingSegment,
    VisemeAvatarAdapter,
    VisualRendererFactory,
    VisualSpec,
    resolve_voice_id,
)

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_check(name: str, check_fn: Callable[[], Tuple[bool, str]]) -> bool:
    print(f"{CYAN}[RUNNING]{RESET} {name}...", end=" ", flush=True)
    start = time.time()
    try:
        passed, details = check_fn()
        elapsed = time.time() - start
        if passed:
            print(f"{GREEN}[PASSED]{RESET} ({elapsed:.2f}s) - {details}")
            return True
        else:
            print(f"{RED}[FAILED]{RESET} ({elapsed:.2f}s) - {details}")
            return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"{RED}[ERROR]{RESET} ({elapsed:.2f}s) - Exception: {e}")
        return False


def test_voice_catalog() -> Tuple[bool, str]:
    hi = resolve_voice_id("hi")
    en_in = resolve_voice_id("en-IN")
    en = resolve_voice_id("en")
    if "Swara" in hi and "Neerja" in en_in and "Aria" in en:
        return True, f"Voices resolved: hi={hi}, en_in={en_in}, en={en}"
    return False, "Voice IDs mismatch"


def test_tts_synthesis() -> Tuple[bool, str]:
    tts = FallbackTTSAdapter()
    res = tts.synthesize("Welcome to Shikshak AI adaptive learning platform.", "en")
    if os.path.exists(res.audio_path) and res.duration_sec > 0 and len(res.word_timestamps) > 0:
        return True, f"Synthesized {res.duration_sec}s audio ({len(res.word_timestamps)} word timestamps)"
    return False, "TTS synthesis failed"


def test_viseme_avatar() -> Tuple[bool, str]:
    avatar = VisemeAvatarAdapter()
    res = avatar.render("Explaining concept", "en", "emphasis")
    if res.frame_count > 0 and res.fps == 24 and os.path.exists(res.frames_dir):
        return True, f"Rendered {res.frame_count} RGBA frames at {res.fps} FPS"
    return False, "Avatar frame generation failed"


def test_equation_renderer() -> Tuple[bool, str]:
    factory = VisualRendererFactory()
    res = factory.render({"type": "equation", "content": "\\int x^2 dx = \\frac{x^3}{3} + C"})
    if os.path.exists(res.image_path) and res.width == 1344 and res.height == 1080:
        return True, f"Rendered 1344x1080 equation slide ({res.image_path})"
    return False, "Equation render failed"


def test_graph_renderer() -> Tuple[bool, str]:
    factory = VisualRendererFactory()
    res = factory.render({"type": "graph", "content": {"type": "bar", "x": ["Q1", "Q2", "Q3"], "y": [12, 19, 24]}})
    if os.path.exists(res.image_path):
        return True, f"Rendered graph slide ({res.image_path})"
    return False, "Graph render failed"


def test_diagram_renderer() -> Tuple[bool, str]:
    factory = VisualRendererFactory()
    res = factory.render({"type": "diagram", "content": {"nodes": ["Client", "API Gateway", "ML Core", "Avatar"]}})
    if os.path.exists(res.image_path):
        return True, f"Rendered diagram slide ({res.image_path})"
    return False, "Diagram render failed"


def test_code_renderer() -> Tuple[bool, str]:
    factory = VisualRendererFactory()
    res = factory.render({"type": "code", "content": {"code": "def hello():\n    return 'world'", "language": "python"}})
    if os.path.exists(res.image_path):
        return True, f"Rendered syntax-highlighted code editor ({res.image_path})"
    return False, "Code render failed"


def test_service_sync_pipeline() -> Tuple[bool, str]:
    service = AvatarVoiceService()
    seg = TeachingSegment(
        node_id="diag_node_01",
        script_text="In this lesson, we study linear algebra and matrix transformations.",
        language="en",
        visual_spec=VisualSpec(type="equation", content="A \\mathbf{x} = \\lambda \\mathbf{x}"),
        avatar_cue="emphasis",
    )
    rendered = service.render_segment_sync(seg)
    if os.path.exists(rendered.video_url) and rendered.duration_sec > 0:
        return True, f"Rendered video segment: {rendered.duration_sec}s, vtt={rendered.captions_vtt_url is not None}"
    return False, "Service sync pipeline failed"


def test_service_async_queue() -> Tuple[bool, str]:
    service = AvatarVoiceService()
    seg = TeachingSegment(
        node_id="diag_async_node",
        script_text="Neural network weights update via backpropagation.",
        language="en",
        visual_spec=VisualSpec(type="diagram", content={"nodes": ["Forward Pass", "Loss Calc", "Backprop"]}),
        avatar_cue="neutral",
    )
    job_id = service.render_segment(seg)
    for _ in range(30):
        status = service.get_status(job_id)
        if status and status.status == "done":
            return True, f"Async job {job_id} reached 'done' with result: {status.result.video_url}"
        time.sleep(0.2)
    return False, "Async job polling timed out"


def main():
    print(f"\n{BOLD}======================================================{RESET}")
    print(f"{BOLD}   SHIKSHAK AI — avatar_voice Diagnostic Suite       {RESET}")
    print(f"{BOLD}======================================================{RESET}\n")

    checks = [
        ("1. Multilingual Neural Voice Resolution", test_voice_catalog),
        ("2. Offline & Resilient TTS Synthesis", test_tts_synthesis),
        ("3. Viseme-Driven 2D Avatar Frame Generation", test_viseme_avatar),
        ("4. Equation Visual Renderer (1344x1080)", test_equation_renderer),
        ("5. Graph Visual Renderer", test_graph_renderer),
        ("6. Diagram Visual Renderer", test_diagram_renderer),
        ("7. Syntax-Highlighted Code Renderer", test_code_renderer),
        ("8. Synchronous Full Pipeline Compositing", test_service_sync_pipeline),
        ("9. Asynchronous Queue & Status Polling", test_service_async_queue),
    ]

    passed_count = 0
    total_count = len(checks)

    for name, fn in checks:
        if run_check(name, fn):
            passed_count += 1

    print(f"\n{BOLD}------------------------------------------------------{RESET}")
    if passed_count == total_count:
        print(f"{GREEN}{BOLD}ALL {total_count}/{total_count} DIAGNOSTIC CHECKS PASSED!{RESET}")
    else:
        print(f"{RED}{BOLD}{passed_count}/{total_count} CHECKS PASSED.{RESET}")
    print(f"{BOLD}======================================================{RESET}\n")

    sys.exit(0 if passed_count == total_count else 1)


if __name__ == "__main__":
    main()
