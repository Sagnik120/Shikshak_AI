# 04_Phases.md — Sequential Build & Verification Phases

> **Methodology**: Each phase is strictly dependency-ordered. Milestone 1 established the production codebase across all modules. Milestone 2 establishes deployment-level interactive testing, module-by-module web testbeds for user validation, automated diagnostic CLI suites, edge-case hardening, and final submission demo recording.

---

## Milestone 1: Production Subsystem Build (Completed)

### Phase 0 — Skeleton `[x]`
- Scaffold repository per `08_Folder_Structure.md`.
- Stub each module's API contract matching `instructions/Contract.md` signatures.
- **Exit Criteria**: Contracts v1.0.0 locked and verified across all modules.

### Phase 1 — Adapters & Ingestion `[x]`
- `rag`: Multi-format file parsers for PDF/DOCX/PPTX/TXT with layout & structure extraction.
- `backend`: `/api/v1/documents/upload` endpoint, session store, `LearnerProfile` persistence.
- **Exit Criteria**: Ingestion of real multi-page PDFs, DOCX, and PPTX extracts clean structured markdown.

### Phase 2 — Core Planning & Retrieval `[x]`
- `rag`: BGE-M3 1024-dim dense/sparse embeddings, ChromaDB vector store, RRF hybrid fusion, BGE cross-encoder reranker.
- `ai_agent_orchestration`: Planner agent produces `LessonPlan` from parsed documents or bare topics.
- **Exit Criteria**: Sample doc + constraints produces valid, pedagogically ordered `LessonPlan`.

### Phase 3 — Explanation & Visual Selection `[x]`
- `ai_agent_orchestration`: Explainer agent generates `TeachingSegment`s with subject-aware visuals.
- `ml_core`: Visual-type classifier/heuristic (math→equation/graph, physics→simulation, programming→code).
- **Exit Criteria**: Every `LessonNode` maps to an appropriate non-generic `visual_spec`.

### Phase 4 — Video Generation `[x]`
- `avatar_voice`: Edge-TTS neural speech with SSML prosody + 24 FPS transparent viseme avatar + 6 visual renderers + FFmpeg 1080p compositor.
- **Exit Criteria**: Produces playable 1080p broadcast MP4 with synchronized visemes, audio, and visual board.

### Phase 5 — Interaction Loop `[x]`
- `ai_agent_orchestration`: Questioner agent emits `InteractionEvent`s at planned checkpoints.
- `frontend`: Question UI captures student responses (MCQ & short answer).
- `backend`: Full-duplex WebSocket turn handling (`/ws/teach`).
- **Exit Criteria**: Interactive teaching session pauses for checkpoints and receives student input.

### Phase 6 — Evaluation, Misconceptions & Adaptation `[x]`
- `ml_core`: Rule-based and semantic similarity scoring + misconception taxonomy pattern matching.
- `ai_agent_orchestration`: Adaptation Controller maps evaluations to `ALLOW`, `MODIFY`, or `REGENERATE` decisions.
- **Exit Criteria**: Incorrect student response triggers targeted diagnostic feedback and an adapted re-explanation.

### Phase 7 — Assessment, Reporting & Learner Profile `[x]`
- `ai_agent_orchestration`: Assessment agent synthesizes session metrics into an `AssessmentReport`.
- `backend`: Report persistence and retrieval via `/api/v1/learners/{id}/report`.
- **Exit Criteria**: Generates comprehensive pedagogical report with mastery scores and next steps.

### Phase 8 — Frontend Classroom & Multilingual Pass `[x]`
- `frontend`: Complete learner UI (`index.html`, `classroom.html`, `report.html`) with telemetry HUD and KaTeX math.
- Multilingual support across English, Hindi, and Hinglish.
- **Exit Criteria**: Full session playable in browser with real-time UI state sync.

### Phase 9 — Documentation & Structural Polish `[x]`
- Restructure documentation library into `docs/spec/` and `docs/system/`.
- Remove redundant duplicate files, obsolete draft fix plans, and empty stubs.
- Produce authoritative root `README.md` and `docs/README.md`.
- **Exit Criteria**: Git working tree clean, documentation hierarchy verified.

---

## Milestone 2: Deployment-Level Testing, Module Web Playgrounds & Issue Resolution (Active)

> **Objective**: Validate the system at actual deployment level (100% real production algorithms, un-mocked execution) by providing dedicated module-wise test scripts and interactive web testbeds for manual user verification, followed by edge-case hardening and bug fixing.

---

### Phase 10 — Module-Wise Diagnostic CLI Test Harnesses `[ ]`

*Goal: Build and verify standalone CLI test runners for every individual module, executing un-mocked production code against real multi-modal data with microsecond timing and failure reports.*

#### Sub-Phase 10.1: RAG Deep Diagnostic CLI Runner
- **10.1.1 Document Parsing Verification**: Execute parsing across real-world multi-page PDFs (complex typography, multi-column), DOCX, PPTX (slide titles + speaker notes), and plain text.
- **10.1.2 Multilingual Structure Extraction**: Verify Devanagari (`[\u0900-\u097F]`) and Bengali (`[\u0980-\u09FF]`) heading detection, Indic numeral normalization (`০-৯` & `०-९` $\rightarrow$ `0-9`), and TF-IDF key-term extraction.
- **10.1.3 Token Budget & Script-Aware Chunking**: Test BGE-M3 tokenizer chunking under script-aware weighting ($2.4\times$ Indic, $1.3\times$ Latin), verifying all chunks satisfy token boundaries ($\le 500$ tokens) with 10% overlap and heading inheritance.
- **10.1.4 Chroma Vector Store & Hybrid Retrieval**: Test embedding generation (1024-dim dense + sparse lexical weights), collection persistence, Reciprocal Rank Fusion (RRF), and cross-encoder reranker score calibration ($0.5001$ baseline vs $0.52$ citation threshold).
- **10.1.5 Topic-Only Mode & Anti-Hallucination Risk**: Test retrieval when `document_id=None`, verifying the system returns `risk_level="no_document_context"` and enforces strict grounding guardrails.
- **Verification Script**: `scripts/run_rag_diagnostics.py`

#### Sub-Phase 10.2: Avatar & Voice Synthesis CLI Diagnostics
- **10.2.1 Cloud Neural TTS & Voice Catalog**: Test Edge-TTS live WebSocket connection, latency benchmarking, and voice catalog resolution across English (`en-IN-NeerjaNeural`), Hindi (`hi-IN-SwaraNeural`), and Bengali (`bn-IN-TanishaaNeural`).
- **10.2.2 Prosody Modulation & Subtitle Extraction**: Verify W3C SSML prosody tag generation (pitch, rate, emphasis, questioning tone) and word/sentence boundary timing event extraction for WebVTT/SRT subtitles.
- **10.2.3 Audio RMS Analysis & 24 FPS Viseme Generation**: Test audio energy envelope calculation (`librosa` RMS) and 24 FPS mouth viseme frame selection (closed, small-open, wide-open, round) with transparent RGBA frames.
- **10.2.4 6 Visual Renderers Verification**: Validate standalone rendering of:
  - LaTeX mathematical equations (`matplotlib.mathtext` / `usetex`).
  - 2D mathematical functions & coordinate plots.
  - 3D surface charts & geometry graphs.
  - Syntax-highlighted code execution panes (`Pygments`).
  - Concept flowcharts & structural diagrams.
  - Key takeaway bullet cards.
- **10.2.5 FFmpeg 1080p Compositor**: Validate FFmpeg `filter_complex` compositor (1920x1080 canvas, 70% main visual board, 30% top-right avatar PiP overlay, bottom burned-in subtitles, and audio muxing).
- **10.2.6 Offline Waveform Fallback**: Verify pure-Python offline sine synthesizer and static PIL compositor activate seamlessly when network is severed.
- **Verification Script**: `scripts/run_avatar_voice_diagnostics.py`

#### Sub-Phase 10.3: AI Agent Orchestration & Live LLM Diagnostics
- **10.3.1 Gemini 2.0 Flash Live API Handshake**: Validate live REST adapter (`httpx`) communication with Google Gemini 2.0 Flash, measuring request latency, JSON repair heuristics, and token usage.
- **10.3.2 PlannerAgent Curriculum Logic**: Test lesson planning across diverse topics ("Newton's Laws of Motion", "Photosynthesis", "Binary Search Trees") and user constraints (Class 6 vs Class 10 vs College, 5 min vs 20 min, English vs Hindi).
- **10.3.3 ExplainerAgent Script & Visual Spec Compliance**: Verify pedagogical explanations, non-generic visual spec generation, and grounding context citations.
- **10.3.4 QuestionerAgent Checkpoint Probes**: Verify dynamic generation of diagnostic MCQs with plausible distractors and open-ended conceptual questions with evaluation rubrics.
- **10.3.5 AssessmentAgent Diagnostic Scoring**: Test end-of-lesson evaluation synthesis, mastery calculation, and learning path next steps.
- **10.3.6 Deterministic SmartMock Fallback**: Verify `SmartMockLLMAdapter` activates deterministically when `GEMINI_API_KEY` is missing or offline, returning schema-valid Pydantic JSON.
- **Verification Script**: `scripts/verify_live_gemini_quality.py`

#### Sub-Phase 10.4: ML Core & Misconception Taxonomy CLI Diagnostics
- **10.4.1 Rule-Based Exact Evaluator**: Test MCQ answer normalization, punctuation stripping, case-insensitive keyword matching, and Boolean expressions.
- **10.4.2 Semantic Overlap & Embedding Distance**: Test free-text student answer evaluation against reference rubrics using embedding similarity thresholds (CORRECT $\ge 0.78$, PARTIAL $0.50 - 0.77$, INCORRECT $< 0.50$).
- **10.4.3 Misconception Taxonomy Pattern Matcher**: Test detection across curated subject inventories:
  - *Physics*: Current vs. voltage confusion, Newton's 3rd law action-reaction cancellation assumption.
  - *Biology*: Respiration vs. breathing confusion, cell wall vs. cell membrane permeability.
  - *Computer Science*: 0-indexing vs. 1-indexing, pass-by-value vs. pass-by-reference confusion.
  - *Mathematics*: Exponent distribution over addition $(a+b)^2 \ne a^2 + b^2$, division by zero.
- **10.4.4 Dynamic Adaptation Decision Matrix**: Verify mapping of `EvaluationResult` to `AdaptationDecision`:
  - Score $\ge 0.85$ $\rightarrow$ `ALLOW` (progress to next concept).
  - Score $0.50 - 0.84$ $\rightarrow$ `MODIFY` (provide targeted hint, adjust pacing).
  - Score $< 0.50$ + Misconception $\rightarrow$ `REGENERATE` (re-explain with simpler analogy & new visual).
  - Repeated failure $\rightarrow$ `HUMAN` (flag for teacher intervention).
- **10.4.5 Visual Type Suggester**: Test rule engine mapping subjects to optimal visual modalities.
- **Verification Script**: `scripts/run_ml_core_diagnostics.py`

#### Sub-Phase 10.5: Backend REST & WebSocket Transport CLI Diagnostics
- **10.5.1 Session & Document Ingestion APIs**: Test FastAPI endpoints (`POST /api/v1/documents/upload`, `POST /api/v1/sessions`, `GET /api/v1/learners/{id}`).
- **10.5.2 HMAC-SHA256 Token Authentication**: Verify cryptographic session token issuance, expiry, and signature validation.
- **10.5.3 Full-Duplex WebSocket Protocol**: Validate message framing on `/ws/teach` (`session_init`, `video_segment`, `checkpoint_question`, `student_answer`, `evaluation_result`, `adaptation_event`, `final_report`).
- **10.5.4 Client Disconnect & Session Rehydration**: Test client disconnection during video generation and graceful state recovery upon reconnect.
- **10.5.5 Non-Blocking Async Job Queue**: Verify video generation runs in background worker thread while WebSocket loop remains responsive (< 50ms heartbeats).
- **Verification Script**: `scripts/run_backend_diagnostics.py`

#### Sub-Phase 10.6: Master Preflight & System Readiness Diagnostic
- Execute single-command multi-tier health certification across all 5 modules simultaneously.
- **Verification Script**: `scripts/preflight_check.py`

---

### Phase 11 — Interactive Module Web Testbeds (Playground UI for Live Manual Verification) `[ ]`

*Goal: Build an interactive, browser-based Module Testbed (`/testbed.html`) mounted on the running backend, allowing the user to provide custom live inputs, execute individual modules in isolation, inspect raw telemetry, and verify deployment-level execution without mocks.*

#### Sub-Phase 11.1: Unified Testbed Frontend Architecture & Shell
- **11.1.1 Responsive Glassmorphism Shell**: Create `modules/frontend/src/testbed.html`, `testbed.css`, and `testbed.js` featuring modern dark-mode aesthetic, navigation tabs for each module, and live status badges.
- **11.1.2 Backend Testbed Router Mount**: Implement `modules/backend/src/routes/testbed.py` exposing isolated endpoints (`/api/v1/testbed/rag`, `/api/v1/testbed/voice`, `/api/v1/testbed/orchestration`, `/api/v1/testbed/mlcore`) and static HTML serving.
- **11.1.3 Real-Time Telemetry & JSON Inspector**: Integrate collapsible raw JSON response viewer, execution stopwatch (latency in ms), and token consumption counter on every testbed tab.

#### Sub-Phase 11.2: Interactive RAG Playground Tab
- **11.2.1 Drag-and-Drop Document Ingestion**: Upload custom PDF, DOCX, PPTX, or TXT files directly from the browser; view extracted text, detected chapters, and section hierarchies.
- **11.2.2 Chunk Token & Budget Inspector**: Visual display of each generated chunk, subword token count, script multiplier badge, and heading metadata.
- **11.2.3 Interactive Vector Search & Reranker Console**: Input arbitrary queries; view top-$k$ retrieved chunks with dense score, sparse score, fused RRF score, and final cross-encoder rerank score.
- **11.2.4 Grounding & Anti-Hallucination Sandbox**: Test queries with document attached vs. topic-only mode; view citation highlights and grounding risk badge (`LOW`, `MEDIUM`, `HIGH`, `NO_CONTEXT`).

#### Sub-Phase 11.3: Interactive Avatar & Voice Playground Tab
- **11.3.1 Multilingual Script & Voice Studio**: Textarea for custom teaching scripts in English, Hindi, Bengali, or Hinglish; voice picker with live preview (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`, `bn-IN-TanishaaNeural`, etc.).
- **11.3.2 Real-Time Neural Audio Player**: Synthesize audio on the fly with live playback, waveform visualization, and WebVTT subtitle stream.
- **11.3.3 24 FPS Viseme Mouth Previewer**: Canvas component displaying real-time 24 FPS mouth viseme animation synchronized with audio phonemes.
- **11.3.4 Dynamic Visual Board Sandbox**: Live editor and renderer for:
  - LaTeX equation previewer (renders dynamic math derivations).
  - 2D/3D function graph generator (input formulas like $f(x) = \sin(x) \cdot e^{-0.1x}$ and render plot).
  - Code execution pane (input Python/JS and preview highlighted code board).
- **11.3.5 One-Click Full Video Render**: Render complete 1080p MP4 segment combining voice + viseme + visual board via FFmpeg; embedded HTML5 video player with download button.

#### Sub-Phase 11.4: Interactive AI Agent Brain Playground Tab
- **11.4.1 Live Curriculum Planner**: Input arbitrary topic (e.g. "Quantum Computing Basics", "Mughal Empire Architecture"), select learner grade and session duration (5 to 60 mins), and inspect generated `LessonPlan` nodes.
- **11.4.2 Explainer Segment Generator**: Inspect generated spoken scripts, visual specifications, and pedagogical analogies for any selected lesson node.
- **11.4.3 Question Generator Sandbox**: Generate checkpoint questions (MCQ or conceptual free-text) with correct answer keys, distractor rationales, and evaluation rubrics.
- **11.4.4 Live LLM Adapter Switcher**: Toggle between live Gemini 2.0 Flash and SmartMock fallback; compare latency and generation quality side-by-side.

#### Sub-Phase 11.5: Interactive ML Core & Pedagogy Evaluation Playground Tab
- **11.5.1 Student Answer Testing Sandbox**: Input a question, reference rubric, and type sample student responses (correct, partially correct, common misconception, or typo-ridden).
- **11.5.2 Dual Scoring Meter**: Visual gauge displaying rule-based exact match vs. embedding semantic similarity score.
- **11.5.3 Misconception Diagnostic Inspector**: Displays detected misconception tag from taxonomy, root cause reasoning, and recommended remedial analogy.
- **11.5.4 Adaptation Action Simulator**: Shows state machine transition (`ALLOW` progress, `MODIFY` hint, `REGENERATE` simpler re-explanation, `HUMAN` mentor alert).

#### Sub-Phase 11.6: Interactive WebSocket & Classroom Stream Playground Tab
- **11.6.1 Real-Time WebSocket Telemetry HUD**: Connect to live `/ws/teach` channel and inspect raw bidirectional JSON frames in real time with timestamped event log.
- **11.6.2 Network Disconnect & Reconnect Simulator**: Simulate network drops, test automatic reconnection handshake, and verify lesson state preservation.
- **11.6.3 Video & Interaction Turn-Taking Testbed**: Walk through a simulated 2-segment mini-lesson: video plays $\rightarrow$ pauses at checkpoint $\rightarrow$ submit answer $\rightarrow$ receives adaptation $\rightarrow$ views final report.

---

### Phase 12 — Deployment-Level Deep Testing, Edge Cases & Bug Resolution `[ ]`

*Goal: Subject the complete system to adversarial inputs, high load, degraded network conditions, and edge cases, resolving every discovered bug, memory leak, and performance bottleneck.*

#### Sub-Phase 12.1: Heavy Multilingual & Formatting Edge Cases
- **12.1.1 Extreme Document Parsing**: Ingest 100+ page textbook PDFs, scanned low-DPI documents (Tesseract OCR), multi-column scientific papers, and corrupted files; verify zero unhandled exceptions.
- **12.1.2 Complex Mathematical LaTeX & 3D Plotting**: Render extreme mathematical expressions (nested matrices, integral equations) and heavy 3D surfaces; verify FFmpeg compositor stability.
- **12.1.3 Deep Code Formatting & Terminal Visuals**: Render syntax-highlighted code blocks with 50+ lines, long lines requiring wrapping, and multi-language syntax (Python, C++, Java).

#### Sub-Phase 12.2: Network, Latency & Resilience Stress Testing
- **12.2.1 Edge-TTS Connection Drop Recovery**: Simulate network severance mid-synthesis; verify automatic failover to offline sine synthesizer and static visual compositor.
- **12.2.2 Gemini API Rate Limits & Network Outage**: Simulate Gemini 429 rate limit or HTTP 503; verify seamless fallback to SmartMock adapter without session crash.
- **12.2.3 WebSocket Jitter & Reconnection**: Test aggressive client reconnection loops, packet reordering, and session token re-validation.

#### Sub-Phase 12.3: Concurrency, Memory & Resource Leak Elimination
- **12.3.1 Concurrent Multi-User Sessions**: Run multiple simultaneous teaching sessions on FastAPI backend; verify vector store client thread safety and isolated session states.
- **12.3.2 FFmpeg Temp File Garbage Collection**: Verify automated cleanup of temporary audio files (`temp_audio/*.mp3`), video frames (`temp_frames/*.png`), and rendered segments.
- **12.3.3 ChromaDB Vector Storage Cleanup**: Ensure temporary test collections are properly disposed of to prevent disk bloat.

#### Sub-Phase 12.4: Comprehensive Bug Fixing & Performance Hardening
- **12.4.1 Defect Tracking & Root-Cause Resolution**: Log and resolve every defect discovered in Sub-Phases 12.1–12.3 in source code.
- **12.4.2 Architectural Postmortem Documentation**: Update `docs/system/issues_faced.md` with in-depth technical postmortems, root-cause analyses, and code diffs.
- **12.4.3 Sub-Second UI Interactivity**: Profile and optimize frontend WebSocket rendering latency to ensure instantaneous feedback.

---

### Phase 13 — Production Certification & Official Demo Recording `[ ]`

*Goal: Execute end-to-end certification across all rubric requirements and record the official 3–7 minute submission walkthrough video demonstrating the autonomous human-like AI educator.*

#### Sub-Phase 13.1: Preflight Health & Rubric Certification
- **13.1.1 Master Preflight Verification**: Run `python scripts/preflight_check.py --require-ffmpeg --check-tier2` with 100% PASS across all subsystems.
- **13.1.2 Automated Regression Suite**: Run full pytest harness (`pytest tests/`) ensuring 100% pass rate across unit, integration, smoke, and eval tests.
- **13.1.3 12 Mandatory Requirements Audit (PS §17)**: Formal verification that all 12 problem statement criteria are demoable in live code.

#### Sub-Phase 13.2: Full-Session Dry Run Verification
- **13.2.1 CLI Dry Run**: Run `python scripts/run_live_demo.py` from start to finish, validating terminal output quality.
- **13.2.2 Browser Dry Run**: Execute complete teaching session on `http://localhost:8000/` verifying audio-visual fidelity, checkpoint pauses, adaptation, and report generation.

#### Sub-Phase 13.3: Official 3–7 Minute Submission Video Recording
- **13.3.1 Step 1: Input & Ingestion**: Upload sample document / input topic ("Photosynthesis" or "Newton's Laws").
- **13.3.2 Step 2: AI Lesson Planning**: Showcase real-time curriculum generation matching grade level and duration.
- **13.3.3 Step 3: Broadcast Video Teaching**: Capture broadcast 1080p teaching video with 24 FPS lip-synced avatar, neural voice, and dynamic LaTeX/graph visual boards.
- **13.3.4 Step 4: Interactive Checkpoint**: Show video pausing and student being prompted with diagnostic question.
- **13.3.5 Step 5: Misconception Detection & Adaptation**: Student enters an intentionally wrong answer $\rightarrow$ AI detects misconception $\rightarrow$ adapts teaching approach with new analogy and simpler visual.
- **13.3.6 Step 6: Diagnostic Assessment & Feedback**: Showcase final assessment report, mastery telemetry, and recommended learning path.

#### Sub-Phase 13.4: Final Submission Readiness Sign-Off
- **13.4.1 Documentation Sign-Off**: Update `docs/spec/09_Progress_Tracker.md` with final verification timestamps and metrics.
- **13.4.2 Final Git Commit & Push**: Commit all code and documentation cleanly to `origin/main`.
