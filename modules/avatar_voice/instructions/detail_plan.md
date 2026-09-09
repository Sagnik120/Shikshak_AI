# detail_plan.md — Avatar & Voice Module (Shikshak AI)

## 1. Goal & Architecture Overview
The `avatar_voice` module generates the multimodal **AI Teaching Video** for Shikshak AI.
Per the Problem Statement and Rubric, an avatar merely reading plain text is **unacceptable**; the teaching video must synchronize on-screen progressive diagrams, equations, syntax-highlighted code, graphs, and timelines alongside expressive avatar facial animations, natural pacing, and multilingual neural speech.

- **Direct Rubric Weight:** 15/100 points (AI Teaching Video Generation) + 10/100 points (Voice & AI Avatar Quality) + contributes to Multilingual Education (10 points).
- **Core Pipeline Contract:** Consumes `TeachingSegment` (Contract §6) and produces `RenderedVideoSegment` (Contract §7).
- **Automated Test Status:** **30 / 30 Automated Tests Passing (100% Green)** across unit, evaluation, integration, and web test suites.

---

## 2. Completed Implementation (Milestone 1)

### 2.1 Multilingual Neural Text-to-Speech (TTS)
- **Primary Engine:** `EdgeTTSAdapter` using Microsoft Edge Neural Cloud voices (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`, `bn-IN-TanishaaNeural`).
- **Resilient Fallback:** `FallbackTTSAdapter` synthesizing 24 kHz acoustic waveform audio offline using pure Python, ensuring zero test or network failure.
- **Pedagogical Prosody & Cues:** Injects SSML prosody rate/pitch shifts mapped to `avatar_cue` (`neutral`, `emphasis`, `questioning`, `encouraging`, `celebratory`).
- **Word-Level Alignment:** Captures boundary events into `word_timestamps` (`WordTimestamp(word, start_sec, end_sec)`) and generates standard WebVTT subtitles.

### 2.2 Dual-Tier Avatar & Lip-Sync Animation
- **Tier 2 (Neural Diffusion):** `MuseTalkAvatarAdapter` leveraging latent diffusion for high-fidelity photorealistic lip-synchronization when GPU/PyTorch checkpoints are available.
- **Tier 1 (Procedural Visemes):** `VisemeAvatarAdapter` generating 24 FPS transparent RGBA frames with RMS energy analysis mapped to 5 viseme stages (`closed`, `slightly_open`, `wide_open`, `o_shape`, `smile`), natural 3.5-second blink intervals, and cue head tilts.
- **Automatic Fallback:** Gracefully falls back from Tier 2 to Tier 1 when GPU or model weights are absent, explicitly populating `tier_used="tier1_viseme"` and `tier_used_reason`.

### 2.3 Subject-Aware Visual Slide Generation (7 Renderers)
- **Canvas Viewport:** 1344 x 1080 (70% split-screen canvas).
- **Mathematical Equations:** `EquationRenderer` supporting LaTeX derivations and progressive step-by-step reveals with bounding-box highlights.
- **Computer Science Code:** `CodeRenderer` with Pygments syntax highlighting, line numbers, variable badges, and terminal output execution panes.
- **Science & Math Graphs:** `GraphRenderer` plotting SymPy/NumPy curves with grid lines, roots, and labeled axes.
- **Engineering Diagrams:** `DiagramRenderer` producing node-link architectural flowcharts and hierarchies via NetworkX / Pillow.
- **Historical Timelines:** `TimelineRenderer` laying out chronological milestones and date cards.
- **Geography Maps:** `MapRenderer` rendering coordinate grids, routes, and geographic landmark markers.
- **Media & External Figures:** `ImageRenderer` formatting diagrams and contextual images.

### 2.4 FFmpeg Video Compositor
- **Output Format:** Full HD 1080p MP4 (1920 x 1080 @ 24 FPS, H.264 / AAC).
- **Layout:** 70% Left Slide (1344 x 1080) + 30% Right Avatar (576 x 1080) + dynamic bottom captions burn-in.
- **Execution:** Headless FFmpeg via `imageio-ffmpeg` static binaries with fallback to system FFmpeg.

---

## 3. Isolated Web Testbed & Structured Logging System (Milestone 2)

To enable comprehensive human and automated verification of each sub-engine without altering or risking the production backend, an isolated web testbed and hierarchical logging engine has been deployed.

### 3.1 Strict Design Constraints
1. **Production Backend Untouched:** Zero modifications to `modules/backend/src/`. Port 8000 remains untouched.
2. **Dedicated Isolated Port:** Testbed server runs exclusively on **Port 8004**.
3. **Light Professional UI Theme:** Crisp white (`#ffffff`), soft slate (`#f8fafc`), subtle borders (`#e2e8f0`), Inter typography, navy/indigo accents. **Dark mode is strictly prohibited.**
4. **Hierarchical Log Traceability:** All inputs, execution checkpoints, outputs, and errors are saved into categorized subdirectories with exact source `.py` file and function name tracking.

### 3.2 Testbed Directory & File Structure
```
modules/avatar_voice/tests/web_test/
├── server.py               # Standalone FastAPI server on Port 8004
├── logger.py               # Hierarchical AvatarVoiceTestLogger engine
├── logs/                   # Categorized log subdirectories (git-tracked via .gitkeep)
│   ├── tts/                # Speech synthesis manifests & text logs
│   ├── avatar/             # Viseme/MuseTalk frame generation logs
│   ├── visuals/            # Slide rendering & progressive step logs
│   ├── compositor/         # FFmpeg filtergraph & video muxing logs
│   ├── service/            # End-to-end sync & async job logs
│   └── errors/             # Stack traces, inputs, and diagnostic logs
└── static/                 # Light professional frontend assets
    ├── index.html          # 5-studio interactive tab layout
    ├── css/
    │   └── style.css       # Clean light design system
    └── js/
        └── app.js          # Pure vanilla JS client connecting to Port 8004
```

### 3.3 Interactive Studios in Web UI
1. **Speech Synthesis Studio (TTS):** Narrate script text, select language (`en`, `hi`, `hinglish`, `bn`), choose provider (`resilient`, `edge`, `fallback`), select pedagogical cue, play generated audio, download WebVTT, and inspect word timestamp table.
2. **Avatar Animation Studio:** Test Tier 1 Visemes vs Tier 2 MuseTalk, preview keyframe carousel, inspect FPS and detected mouth states.
3. **Multi-Subject Visuals Studio:** Test all 7 visual subject types with pre-loaded presets, render 1344x1080 slides, and step through progressive math derivations.
4. **1080p Video Compositor Studio:** Compose complete 1920x1080 teaching video segments end-to-end with synchronous playback.
5. **Structured Log Explorer:** Filter logs by category, inspect execution details, verify exact `source_file` and `source_function`, and trace any model or rendering hallucination.

### 3.4 Structured Logging Architecture
Every test run generates both a machine-readable JSON manifest and a formatted plain text `.log` file:
- **Filename Convention:** `YYYYMMDD_HHMMSS_<category>_<log_id>.json` / `.log`
- **Tracked Metadata:**
  ```json
  {
    "log_id": "b66690c7",
    "timestamp": "2026-09-09T19:30:00.123456",
    "category": "tts",
    "operation": "speech_synthesis",
    "source_file": "modules/avatar_voice/src/tts/edge_tts_adapter.py",
    "source_function": "synthesize",
    "status": "success",
    "input": { ... },
    "checkpoints": [ ... ],
    "output": { ... },
    "error": null
  }
  ```
- If an error occurs, it is automatically written to `logs/errors/` capturing the full Python exception traceback and the exact input that triggered it.

---

## 4. How to Run & Verify the Testbed

### 4.1 Launch the Testbed Server
```bash
python modules/avatar_voice/tests/web_test/server.py
```
Server runs on: **`http://localhost:8004`**

### 4.2 Run Automated Tests
```bash
# Run isolated testbed unit tests
pytest modules/avatar_voice/tests/unit/test_avatar_voice_web_test_server.py -v

# Run entire avatar_voice module test suite (30 passing tests)
pytest modules/avatar_voice/tests/ -v
```
