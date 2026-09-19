# Avatar & Voice Web Test Details

## 1. Purpose
This document provides the definitive manual web-test specification for the Shikshak AI Avatar & Voice module. It defines exactly what a human tester should enter into the isolated Avatar & Voice web testbed (`Port 8004`), the expected outputs, PASS/FAIL criteria, and the distinction between deterministic/local execution and external dependencies (like Edge-TTS or MuseTalk). 

## 2. Scope and Production-Parity Principle
The web testbed (`server.py`) directly invokes the **production `AvatarVoiceService`** and its underlying pipeline of TTS synthesis, Avatar frame generation, Visual rendering, and FFmpeg video compositing. The primary goal of these isolated tests is to prove that the complete media generation pipeline correctly honors the internal `TeachingSegment` contract before it is integrated into the larger Shikshak AI ecosystem.

**If functionality passes here using the real dependencies, the media artifact generation is proven.** However, isolated testing does NOT validate backend websocket streaming, frontend video player integration, or the Orchestrator's state transitions.

## 3. Web-Test Components
The isolated web testbed contains tabs for testing:
1. Speech Synthesis (TTS)
2. Avatar & Lip-Sync (Viseme/MuseTalk)
3. Multi-Subject Visuals (Slides/Progressive Reveals)
4. 1080p Full Video (FFmpeg Composition)
5. Structured Log Explorer

---

## 4. Execution Modes
* **Local / Deterministic:** Validates procedural visual rendering (e.g., LaTeX), procedural viseme frame generation (Tier 1 Avatar), and local FFmpeg compositing.
* **Local Model:** Validates the heavy neural network pipeline for MuseTalk (Tier 2 Avatar) if the environment supports it.
* **Live External Dependency:** Validates the Edge-TTS network request for voice generation.
* **Full E2E:** Out of scope for this isolated testbed; involves Frontend -> Backend -> Orchestrator -> Avatar & Voice.

*Note: The Gemini API is **not required** for the tested Avatar & Voice production paths. No tests in this suite depend on the LLM.*

---

## 5. Speech Synthesis (TTS) Test Cases

* **Production Path:** `TTSFactory.get_adapter()` -> `EdgeTTSAdapter.synthesize()`
* **Output Contract:** `TTSResult` (Audio path, Duration, Word timestamps, WebVTT)

### TTS-01: Normal English Narration (LIVE EXTERNAL DEPENDENCY — HUMAN TEST)
* **Execution Mode:** LIVE EXTERNAL
* **Input:** Script: `"In Newton's second law, force equals mass multiplied by acceleration. The equation is F equals m a."` | Language: `en`
* **Expected Output:** Synthesis succeeds.
* **PASS Criteria:** Valid audio artifact (e.g., `.wav` or `.mp3`) is generated, playable, duration > 0, and a WebVTT file with word timestamps is present.

### TTS-02: Physics Script With Equations (LIVE EXTERNAL)
* **Execution Mode:** LIVE EXTERNAL
* **Input:** Script: `"According to Ohm's Law, voltage equals current multiplied by resistance. V equals I times R."`
* **PASS Criteria:** Audio correctly reads out the equation smoothly without processing failure.

### TTS-03: Longer Teaching Script (LIVE EXTERNAL)
* **Execution Mode:** LIVE EXTERNAL
* **Input:** A moderate 3-4 sentence explanation.
* **PASS Criteria:** Audio is generated without truncation, server doesn't crash or timeout, timestamps cover the full duration.

### TTS-04: Empty Script
* **Execution Mode:** Deterministic
* **Input:** Script: `""` (Empty string)
* **PASS Criteria:** Controlled validation error; no invalid or corrupted audio artifact is produced.

---

## 6. Avatar & Lip-Sync Test Cases

* **Production Path:** `AvatarFactory.get_adapter()` -> `VisemeAvatarAdapter` or MuseTalk implementation.
* **Output Contract:** `AvatarRenderResult` (Frames dir, frame count, 24 FPS, duration, tier used)

### AV-01: Normal Script Context (Tier 1 Viseme)
* **Execution Mode:** Local / Deterministic
* **Input:** Script: `"Let us derive the quadratic formula step by step."` | Tier: `tier1_viseme`
* **Expected Output:** Frame sequence corresponding to the audio duration.
* **PASS Criteria:** Output directories contain a sequence of 24 FPS transparent frames representing viseme mouth states, matching the script length.

### AV-04: Empty Script
* **Execution Mode:** Deterministic
* **Input:** Script: `""`
* **PASS Criteria:** Controlled validation error; no corrupt frame artifacts generated.

### AV-07: Each Supported Avatar Tier (MuseTalk / Tier 2)
* **Execution Mode:** Local Model (If Supported)
* **Input:** Select `tier2_musetalk` with a standard script.
* **PASS Criteria:** Output generates corresponding MuseTalk frames. 
* **Note:** *If environment constraints prevent MuseTalk execution, this should gracefully fallback to `tier1_viseme` or be marked as NOT TESTED.*

---

## 7. Multi-Subject Visual Test Cases

* **Production Path:** `VisualRendererFactory.render()`
* **Output Contract:** `VisualRenderResult` (Image path, 1344x1080, step paths)

### VS-01: Mathematics / LaTeX
* **Execution Mode:** Local / Deterministic
* **Input:** Subject Type: `equation` | Content: `x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}`
* **Expected Output:** A 1344x1080 rendered image slide.
* **PASS Criteria:** LaTeX renders correctly without syntax errors, output dimensions strictly match 1344x1080.

### VS-02: Progressive Reveal
* **Execution Mode:** Local / Deterministic
* **Input:** Content with 4 defined progressive steps (e.g. step-by-step derivation).
* **PASS Criteria:** Output contains multiple image paths in `step_image_paths` preserving the correct sequence.

### VS-04: Invalid LaTeX
* **Execution Mode:** Local / Deterministic
* **Input:** Content: `\frac{unclosed bracket`
* **PASS Criteria:** Graceful fallback or controlled error; server must not crash.

---

## 8. 1080p Full Video Test Cases

* **Production Path:** `AvatarVoiceService.render_segment()` -> `FFmpegCompositor.compose()`
* **Output Contract:** `RenderedVideoSegment` (Video URL, Duration, VTT URL)

### VID-01: Normal Complete Teaching Segment (P0 - MUST TEST)
* **Execution Mode:** LIVE EXTERNAL (for TTS) + LOCAL COMPOSITION
* **Input:** 
  * Node ID: `node_math_quadratic_001`
  * Narration: `"The quadratic formula helps us find the roots of any quadratic equation."`
  * Visual Type: `equation`
  * Avatar Tier: `tier1_viseme`
* **Expected Output:** A fully composited MP4 video artifact.
* **PASS Criteria:** 
  - Output is strictly 1920x1080 resolution.
  - Video framerate is exactly 24 FPS.
  - Split-screen layout correctly positions the avatar alongside the 1344x1080 visual slide.
  - Audio/Video synchronization is stable (no desync).
  - WebVTT captions exist and align with speech.

### VID-07: Empty Narration
* **Execution Mode:** Deterministic
* **Input:** Empty script for full video.
* **PASS Criteria:** Controlled validation error; pipeline stops early and does not generate a broken FFmpeg composition.

---

## 9. Structured Logging Test Cases

### LOG-01 to LOG-05: Verification
* **Execution Mode:** Local
* **Tests:** Submit a full video rendering job, then check the Structured Log Explorer UI.
* **PASS Criteria:**
  - Structured logs capture the progression of the async rendering pipeline (`queued` -> `synthesizing_audio_and_visuals` -> `animating_avatar` -> `compositing_video` -> `completed`).
  - No secret `.env` variables or API keys are written to the logs.

---

## 10. Gemini / External Dependency Matrix

| Component | Gemini Used? | External/Local Dependency | Human Live Test Required? | Evidence |
|---|:---:|---|:---:|---|
| TTS | No | Edge-TTS (External network API) | Yes | `tts/factory.py`, `EdgeTTSAdapter` |
| Avatar | No | MuseTalk (Local heavy model) or Viseme (Local) | Yes | `avatar/viseme_avatar.py` |
| Visuals | No | Matplotlib/Pillow (Local renderers) | No | `visuals/factory.py` |
| Video | No | FFmpeg (Local binary) | No | `compositor/ffmpeg_compositor.py` |

*Gemini API is not required for the tested Avatar & Voice production paths.*

---

## 11. Production-Parity Mapping

| Web Test | Actual Production Function | Dependency | Output | Downstream Consumer |
|---|---|---|---|---|
| TTS | `TTSFactory.get_adapter().synthesize()` | Edge-TTS API | `TTSResult` | Avatar generation / Compositing |
| Avatar | `AvatarFactory.get_adapter().render()` | Local Procedural / MuseTalk | `AvatarRenderResult` | Compositing |
| Visuals | `VisualRendererFactory.render()` | Pillow/Matplotlib | `VisualRenderResult` | Compositing |
| Full Video | `AvatarVoiceService.render_segment()` | FFmpeg | `RenderedVideoSegment` | AI Orchestrator (`TeachingSegment` translation) & Frontend Video Player |

---

## 12. Test Execution Order

1. **Phase 1 — TTS:** Validate Edge-TTS network capability and `.vtt` artifact structure.
2. **Phase 2 — Visuals:** Validate LaTeX and image processing dimensions (1344x1080).
3. **Phase 3 — Avatar:** Validate 24 FPS transparent viseme frame generation matching TTS audio.
4. **Phase 4 — Video (P0):** Validate the FFmpeg compositor merging all three previous pipelines into a compliant 1920x1080@24FPS `.mp4`.
5. **Phase 5 — Logging:** Verify async job tracking and error catching.
6. **Phase 6 — E2E:** Verify the final integration of this media artifact into the frontend player.

---

## 13. PASS/FAIL Recording Template

```text
Test ID:
Priority:
Component:
Execution Mode: [LOCAL / LIVE EXTERNAL / LOCAL MODEL]
Input:
Action:
Expected Output:
PASS Criteria:
FAIL Indicators:
Actual Result:
Status: [PASS / PARTIAL / FAIL / NOT TESTED / DEFERRED]
Artifact:
Notes:
```

## 14. Remaining E2E Validation
Passing an isolated Avatar & Voice web test proves that the tested production media path successfully generates compliant 1080p video artifacts under that configuration. 
**It does NOT automatically prove:**
- Backend JSON serialization and file serving of the `.mp4`.
- Frontend video player synchronization and CSS layout.
- The `TeacherOrchestrator` successfully feeding the correct `TeachingSegment` schema during the FSM loop.
- Concurrent multi-user rendering server load.
