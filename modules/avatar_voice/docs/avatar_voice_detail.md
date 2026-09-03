# Avatar & Voice Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `avatar_voice`  
> **Repository Path**: `modules/avatar_voice/`  
> **Primary Phase**: Phase 4 (AI Teaching Video Generation)  
> **Status**: **STABLE / PRODUCTION-READY** (Phase 4 fully verified with 10 unit/integration test suites)  
> **Key Contracts**: Contract §6 (`TeachingSegment`), Contract §7 (`RenderedVideoSegment`), Contract §14 (`AvatarAdapter`, `TTSAdapter`)

---

## 1. The Task (In Simple Language)

Imagine a teacher standing at the front of a smart classroom. The teacher does three things at once:
1. **Speaks clearly** in the language the student understands (English, Hindi, or Hinglish) with natural pacing and expression.
2. **Animates their face and body** (talking, blinking, tilting their head when asking a question, or gesturing when emphasizing a key point).
3. **Presents visual aids on the blackboard** (drawing math equations, graphing parabolas, showing programming code with highlighted keywords, or charting historical timelines).

The **`avatar_voice`** module is the digital realization of this physical teacher. It takes a lesson script written by the AI orchestrator, generates human-like synthetic voice narration, animates a synchronized 2D teacher avatar that speaks that narration, creates high-resolution visual slides matching the subject, and composites them into an ultra-smooth 1080p MP4 educational video with synchronized subtitles.

Without this module, Shikshak AI would just be a text chatbot. With this module, Shikshak AI becomes an engaging, human-like video educator that students can watch and listen to.

---

## 2. Technical Details & Architecture

The module is engineered as an asynchronous, multi-stage multimedia synthesis pipeline following modern software design patterns:

- **Facade Pattern (`AvatarVoiceService`)**: Provides a clean, single-entry interface for both synchronous and non-blocking asynchronous job rendering.
- **Adapter Pattern (`TTSAdapter`, `AvatarAdapter`)**: Encapsulates external speech engines and neural avatar models behind strict abstract base classes, enabling zero-code-change vendor switching per Contract §14.
- **Factory Pattern (`TTSFactory`, `VisualRendererFactory`)**: Dynamically resolves and instantiates the proper text-to-speech engine and visual renderer based on configuration or visual type.
- **Resilient Fallback Design**: All multimedia components operate with pure-Python offline fallbacks (synthesizing acoustic audio waveforms and PIL-based compositing), ensuring 100% test and offline execution reliability even in environments lacking GPU acceleration, system FFmpeg, or internet access.

### Visual Canvas Composition Layout (1920x1080 FHD)
```
+-----------------------------------------------------------------------------+
| Shikshak AI Virtual Classroom (1920x1080 @ 24 FPS)                          |
| +-----------------------------------------------+ +-----------------------+ |
| |                                               | |  Avatar Picture-in-   | |
| |       70% Main Visual Viewport                | |  Picture (PiP)        | |
| |       (1344 x 1080)                           | |  (576 x 540, Top-Rt)  | |
| |                                               | |  Transparent RGBA     | |
| |  [Equations / Graphs / Code / Diagrams]       | |  Viseme Lip-Sync      | |
| |                                               | +-----------------------+ |
| |                                               |                           |
| |                                               |  [Subject / Concept Meta] |
| |                                               |                           |
| +-----------------------------------------------+                           |
| +-------------------------------------------------------------------------+ |
| | Subtitle Bar (Bottom 100px Overlay): WebVTT Word-Level Synced Captions   | |
| +-------------------------------------------------------------------------+ |
+-----------------------------------------------------------------------------+
```

---

## 3. What is Implemented Till Now (Current Status)

| Subsystem | Implementation Details | Status |
|---|---|---|
| **Contract Schemas** | Pydantic v2 schemas for `TeachingSegment`, `RenderedVideoSegment`, `VisualSpec`, `WordTimestamp`, `TTSResult`, `AvatarRenderResult`, `VisualRenderResult`. | **100% Complete & Tested** |
| **Multilingual TTS** | `EdgeTTSAdapter` supporting Microsoft Neural Voices (`hi-IN-SwaraNeural`, `hi-IN-MadhurNeural`, `en-IN-NeerjaNeural`, `en-US-AriaNeural`) with word boundary timestamp parsing and WebVTT creation. | **100% Complete & Tested** |
| **Acoustic Fallback TTS** | `FallbackTTSAdapter` pure-Python mathematical sine/harmonic audio generator for offline environments. | **100% Complete & Tested** |
| **Resilient TTS Factory** | `TTSFactory.get_adapter("resilient")` automatic online-to-offline fallback wrapper. | **100% Complete & Tested** |
| **Viseme 2D Avatar** | `VisemeAvatarAdapter` Tier 1 engine: calculates audio RMS energy, generates 24 FPS transparent RGBA frames, dynamically switches 4 mouth visemes (`closed`, `slightly_open`, `wide_open`, `o_shape`), natural 3-4s blink cycle, and cue-reactive poses (`neutral`, `emphasis`, `questioning`). | **100% Complete & Tested** |
| **Wav2Lip Neural Avatar** | `Wav2LipAvatarAdapter` Tier 2 neural model skeleton adapter with graceful fallback to Tier 1 visemes. | **Scaffolded / Fallback Active** |
| **Visual Renderers** | 6 specialized renderers: `EquationRenderer` (LaTeX / Math), `GraphRenderer` (Matplotlib), `CodeRenderer` (Syntax-highlighted code slides), `DiagramRenderer` (Structured nodes/arrows), `TimelineRenderer` (Chronological milestones), `MapRenderer` (Geographical landmarks), plus `ImageRenderer`. | **100% Complete & Tested** |
| **Compositor Engine** | `FFmpegCompositor`: Assembles visual slide (1344x1080), avatar PiP (576x540), audio track, and bottom subtitle box into MP4 H.264. Includes pure-Pillow software compositor fallback. | **100% Complete & Tested** |
| **Unified Service Facade** | `AvatarVoiceService`: Synchronous `render_segment_sync()` and thread-safe async queue `render_segment()` with job polling `get_status()`. | **100% Complete & Tested** |
| **Automated Verification** | 10 test suites covering models, TTS, visemes, visual distinctness, compositor layouts, and async queues across `modules/avatar_voice/tests/` and root `tests/`. | **35+ Unit/Integration Tests Passing** |

---

## 4. Full File Structure

```
modules/avatar_voice/
├── __init__.py                                 # Module export interface
├── docs/
│   └── avatar_voice_detail.md                  # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Local copy of cross-module contracts §6 & §7
│   ├── detail_plan.md                          # Phase 4 execution milestones
│   ├── detailed_design_avatar_voice.md         # Low-level 28KB architectural specification
│   └── overview.md                             # High-level module summary
├── src/
│   ├── __init__.py                             # Re-exports AvatarVoiceService, TeachingSegment, RenderedVideoSegment
│   ├── models.py                               # Authoritative Pydantic schemas (Contracts §6 & §7 + domain types)
│   ├── service.py                              # Unified service facade and async worker pool
│   ├── avatar/
│   │   ├── __init__.py                         # Exposes AvatarAdapter, VisemeAvatarAdapter, Wav2LipAvatarAdapter
│   │   ├── base.py                             # Abstract Base Class AvatarAdapter (Contract §14)
│   │   ├── viseme_avatar.py                    # Tier 1 2D viseme animated teacher avatar engine (@ 24 FPS)
│   │   └── wav2lip_avatar.py                   # Tier 2 neural lip-sync model adapter skeleton
│   ├── compositor/
│   │   ├── __init__.py                         # Exposes FFmpegCompositor
│   │   └── ffmpeg_compositor.py                # 1920x1080 split-screen FFmpeg & PIL video compositor
│   ├── tts/
│   │   ├── __init__.py                         # Exposes TTSAdapter, EdgeTTSAdapter, FallbackTTSAdapter, TTSFactory
│   │   ├── base.py                             # Abstract Base Class TTSAdapter (Contract §14) & Language Map
│   │   ├── edge_tts_adapter.py                 # Microsoft Edge-TTS async multilingual neural voice adapter
│   │   ├── fallback_adapter.py                 # Pure-Python acoustic waveform generator (zero network dependency)
│   │   └── factory.py                          # Resilient TTS factory with automatic degradation
│   └── visuals/
│       ├── __init__.py                         # Exposes VisualRendererFactory and all renderer classes
│       ├── base.py                             # BaseVisualRenderer abstract class and canvas constants
│       ├── code_renderer.py                    # Monospace code slide renderer with dark terminal theme
│       ├── diagram_renderer.py                 # Concept flowchart and node-link diagram renderer
│       ├── equation_renderer.py                # Mathematical LaTeX and formula renderer with auto-scaling
│       ├── factory.py                          # VisualRendererFactory routing visual_type strings
│       ├── graph_renderer.py                   # Function and statistical plot renderer via Matplotlib
│       ├── image_renderer.py                   # External and generated image slide adapter
│       ├── map_renderer.py                     # Historical, geographical, and schematic map renderer
│       └── timeline_renderer.py                # Chronological horizontal event track renderer
└── tests/
    ├── conftest.py                             # Pytest fixtures and mock audio/segment generators
    ├── unit/
    │   ├── test_avatar.py                      # Viseme modulation, blink intervals, and cue orientation tests
    │   ├── test_models.py                      # Pydantic validation of TeachingSegment and RenderedVideoSegment
    │   ├── test_tts.py                         # Voice resolution, fallback generation, and WebVTT tests
    │   └── test_visuals.py                     # Visual distinctness and syntax highlighting tests
    └── integration/
        └── test_compositor.py                  # Canvas dimension verification and fallback compositing tests
```

---

## 5. Detailed File Logic (What Each File Actually Does)

### Core & Service Layer
- **[`src/models.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/models.py)**:
  - Defines `VisualSpec`: validates visual type (`equation|graph|diagram|code|image|timeline|map|simulation`) and content (LaTeX, JSON dictionary, code string).
  - Defines `TeachingSegment` (Contract §6): enforces `node_id`, `script_text`, `language`, `visual_spec`, and `avatar_cue` (`neutral`, `emphasis`, `questioning`).
  - Defines `RenderedVideoSegment` (Contract §7): validates output `node_id`, `video_url`, verified `duration_sec`, and optional `captions_vtt_url`.
  - Defines internal tracking models: `WordTimestamp`, `TTSResult`, `AvatarRenderResult`, `VisualRenderResult`, and `RenderJobStatus`.
- **[`src/service.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/service.py)**:
  - Implements `AvatarVoiceService`. Holds instances of `TTSAdapter`, `AvatarAdapter`, `VisualRendererFactory`, and `FFmpegCompositor`.
  - `render_segment_sync(segment)`: Sequentially executes TTS -> Visual Rendering -> Avatar Generation -> Video Composition and returns a `RenderedVideoSegment`.
  - `render_segment(segment)`: Generates a unique `job_id`, registers a `RenderJobStatus`, submits the task to a Python `ThreadPoolExecutor`, and returns the `job_id` immediately without blocking the caller.
  - `_execute_async_job(job_id, segment)`: Background worker method updating progress percentages (25% -> 60% -> 85% -> 100%) and capturing any exceptions into `error`.
  - `get_status(job_id)`: Thread-safe polling lookup for background rendering jobs.

### Speech Synthesis Layer (`src/tts/`)
- **[`src/tts/base.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/tts/base.py)**:
  - Declares abstract method `synthesize(text, language, voice_id) -> TTSResult`.
  - Maps language codes (`en`, `hi`, `hinglish`) to default neural voice names (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`).
- **[`src/tts/edge_tts_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/tts/edge_tts_adapter.py)**:
  - Connects to Microsoft Edge TTS asynchronous web socket service.
  - Parses raw byte stream into an MP3 file, extracts boundary event timestamps down to the millisecond, and formats a compliant `.vtt` WebVTT subtitle track.
- **[`src/tts/fallback_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/tts/fallback_adapter.py)**:
  - Generates synthetic 440Hz / 880Hz harmonic audio waves encoded directly into valid RIFF WAV audio.
  - Computes exact duration based on a human speaking rate heuristic (~140 words per minute) and generates synthetic word timestamps for testing and offline runs.
- **[`src/tts/factory.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/tts/factory.py)**:
  - `TTSFactory.get_adapter(provider_type)`: Instantiates `EdgeTTSAdapter` or `FallbackTTSAdapter`. Under `"resilient"` mode, dynamically tries Edge-TTS and gracefully degrades to `FallbackTTSAdapter` if network calls fail.

### Avatar Animation Layer (`src/avatar/`)
- **[`src/avatar/base.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/avatar/base.py)**:
  - Abstract base class declaring `render(script_text, language, avatar_cue, audio_path) -> AvatarRenderResult`.
- **[`src/avatar/viseme_avatar.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/avatar/viseme_avatar.py)**:
  - Reads generated audio, computes windowed Root-Mean-Square (RMS) amplitude envelopes at 24 FPS.
  - Modulates mouth height and aperture across 4 viseme stages (`closed`, `slightly_open`, `wide_open`, `o_shape`).
  - Implements procedural eye blinking every 72–96 frames (3–4 seconds) with a 4-frame realistic eyelid closing/opening curve.
  - Modulates facial cues according to `avatar_cue`:
    - `neutral`: Balanced eye gaze and neutral brow position.
    - `emphasis`: Slightly raised brows, alert gaze, forward tilt.
    - `questioning`: Asymmetric eyebrow raise (curious look) with subtle head tilt.
  - Emits transparent RGBA PNG frames ready for overlay composition.
- **[`src/avatar/wav2lip_avatar.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/avatar/wav2lip_avatar.py)**:
  - Prepares video tensor preprocessing for neural talking-face generation, safely delegating to `VisemeAvatarAdapter` when deep-learning weights are absent.

### Visual Presentation Layer (`src/visuals/`)
- **[`src/visuals/base.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/base.py)**:
  - Base class enforcing standard dimensions (1344 x 1080) and dark educational canvas styling (`#1E1E2E` background, high-contrast readable typography).
- **[`src/visuals/equation_renderer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/equation_renderer.py)**:
  - Formats mathematical equations, formulas, and expressions. Uses Matplotlib mathtext / LaTeX engine to render crisp mathematical equations with auto-scaling to prevent overflow.
- **[`src/visuals/graph_renderer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/graph_renderer.py)**:
  - Plots mathematical curves (e.g. parabolas, sine waves, coordinate grids) or statistical charts with labeled axes, legends, and styling.
- **[`src/visuals/code_renderer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/code_renderer.py)**:
  - Renders code snippets into an IDE-like dark theme window with mock window controls (macOS red/yellow/green dots), line numbers, and token highlighting for keywords, strings, comments, and functions.
- **[`src/visuals/diagram_renderer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/diagram_renderer.py)**:
  - Draws structured flowchart boxes, arrows, and relational hierarchy diagrams from structured JSON inputs.
- **[`src/visuals/timeline_renderer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/timeline_renderer.py)**:
  - Draws a horizontal chronological timeline with milestone nodes, dates, and event descriptions for history or sequential topics.
- **[`src/visuals/map_renderer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/map_renderer.py)**:
  - Renders coordinate landmarks, route arrows, and geographic reference cards.
- **[`src/visuals/image_renderer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/image_renderer.py)**:
  - Loads, scales, and centers local images or generated visual assets with aspect-ratio preservation.
- **[`src/visuals/factory.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/visuals/factory.py)**:
  - Dispatches `visual_spec.type` string to the appropriate renderer class.

### Video Compositor Layer (`src/compositor/`)
- **[`src/compositor/ffmpeg_compositor.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/src/compositor/ffmpeg_compositor.py)**:
  - Builds an FFmpeg complex filter command:
    `[visual_slide] + [avatar_frames_overlay_top_right] + [bottom_subtitle_bar] + [audio_track] -> output.mp4`.
  - Encodes with `libx264` (`yuv420p` pixel format for universal browser player compatibility) and `aac` audio.
  - Implements an autonomous PIL/Pillow software fallback compositor that composites static video preview frames with exact duration metadata if FFmpeg binaries are missing.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
                       [AI Orchestration: Explainer Agent]
                                        |
                                        v
                 TeachingSegment JSON (Contract §6)
           {node_id, script_text, language, visual_spec, avatar_cue}
                                        |
                                        v
                      [AvatarVoiceService.render_segment()]
                                        |
             +--------------------------+--------------------------+
             |                                                     |
  (1) [TTSAdapter.synthesize]                            (2) [VisualRendererFactory.render]
      - Resolves voice (e.g. Swara/Neerja)                   - Dispatches visual_spec.type
      - Generates audio file (.mp3 / .wav)                   - Renders 1344x1080 graphic slide
      - Extracts word timestamps & .vtt                      - Returns visual image path
             |                                                     |
             +--------------------------+--------------------------+
                                        |
                                        v
                          (3) [AvatarAdapter.render]
                              - Receives audio file & script
                              - Calculates RMS volume curve @ 24 FPS
                              - Renders lip-synced RGBA teacher frames
                              - Applies avatar_cue (neutral/emphasis/questioning)
                                        |
                                        v
                        (4) [FFmpegCompositor.compose]
                            - Assembles 1920x1080 canvas
                            - Overlays visual slide (left 70%)
                            - Overlays avatar PiP (top-right 30%)
                            - Burns / references VTT captions
                            - Muxes synchronized AAC audio
                                        |
                                        v
                      RenderedVideoSegment (Contract §7)
               {node_id, video_url, duration_sec, captions_vtt_url}
                                        |
                                        v
                       [Backend / Frontend Video Player]
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Inbound** | `ai_agent_orchestration` | **Contract §6** (`TeachingSegment`) | In-memory python call or internal service queue with `node_id`, `script_text`, `language`, `visual_spec`, `avatar_cue`. |
| **Inbound** | `ml_core` | **Contract §5 / §6** (`visual_type`) | `ml_core` suggested visual type informs the `visual_spec.type` generated by the orchestrator. |
| **Outbound** | `backend` | **Contract §7** (`RenderedVideoSegment`) | Returns video file path, duration, and WebVTT caption path for persistence in Postgres and streaming to clients. |
| **Outbound** | `frontend` | **Contract §7** (`RenderedVideoSegment`) | Center video player in the frontend loads `video_url` and attaches `captions_vtt_url` to the HTML5 `<track>` element. |
| **Outbound** | `mlops` | **Contract §14** (`Adapter Interfaces`) | Service registry and cache manager cache rendered segments keyed by `(node_id, hash(script_text), language, avatar_cue)`. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`avatar_voice`** module is the execution engine for the **Explain** and **Demonstrate** stages:
1. **RAG** ingests and grounds the lesson material.
2. **AI Orchestration** builds the `LessonPlan` nodes.
3. For each node, **AI Orchestration** drafts a `TeachingSegment`.
4. **`avatar_voice`** receives this segment and physically creates the multimedia teaching segment.
5. The student watches the generated teacher explain and demonstrate the concept.
6. Once the video segment concludes, **AI Orchestration** triggers the **Question** stage via an `InteractionEvent`.

---

## 9. Critical Notes for Any LLM Agent Working on This Module

> [!IMPORTANT]
> **Strict Guardrails for LLM Agents:**
> 1. **Never Break Contract Schemas**: Any modification to `TeachingSegment` or `RenderedVideoSegment` fields will break `ai_agent_orchestration` and `backend`. All changes must strictly follow `instructions/Contract.md` §6 and §7.
> 2. **Always Preserve Pure-Python Fallbacks**: Do not remove `FallbackTTSAdapter` or the PIL fallback in `FFmpegCompositor`. These fallbacks are vital for CI/CD test runners, automated grading scripts, and offline environments where external network access or FFmpeg binaries are missing.
> 3. **Video Canvas Dimensions**: The visual viewport is locked at `1344 x 1080` (70% width) and the avatar PiP is locked at `576 x 540` (30% width). All new visual renderers must inherit from `BaseVisualRenderer` and respect `CANVAS_WIDTH = 1344` and `CANVAS_HEIGHT = 1080`.
> 4. **Multilingual Pacing**: When generating Hindi (`hi`) or Hinglish scripts, Edge-TTS neural voices take approximately 15–20% longer than English for equivalent semantic content. Never hardcode static duration assumptions; always read `duration_sec` from the synthesized `TTSResult`.
> 5. **Thread Safety**: `AvatarVoiceService` uses a Python `ThreadPoolExecutor` and `threading.Lock()` to manage `_jobs`. Any new state added to the service must be thread-safe.
