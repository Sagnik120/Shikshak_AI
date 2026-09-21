# 06_Memory.md — System Living Memory Bank & Fast-Context Cache

> **MANDATORY AGENT DIRECTIVE**:  
> You are reading the **L2 Operational Ground Truth** of the Shikshak AI repository.  
> 1. **Do NOT scan 60+ repository files** on startup. Read this file + [`instructions/Contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md) to obtain 95% operational context.  
> 2. **Never finish your turn without updating this file** if you wrote, modified, refactored, or tested code.

---

## 1. Agent Protocol & Memory Maintenance Rules

Every AI agent operating in this repository **MUST** adhere to the following five operational rules:

### Rule 1: Read-First Fast Path (Token Economy)
- On fresh or resumed sessions, inspect **Section 2 (Active State)** and **Section 3 (File Map)**.
- Only open specific module files (`modules/<name>/src/...`) relevant to your assigned task.

### Rule 2: Strict "Zero Silent Changes" Contract
- Whenever you make changes:
  1. Record what was built, modified, or tested in **Section 6 (Phase Log)**.
  2. Advance the **Active Focus** and **Immediate Next Steps** in **Section 2**.
  3. If you introduced a design decision, fallback, or invariant, add it to **Section 5**.
- **Leaving `06_Memory.md` stale or out of sync with committed code is a protocol violation.**

### Rule 3: Standard Phase Log Entry Schema
Every entry in the Phase Log must strictly adhere to this format:
```markdown
### [Phase X.Y] <Title> — <YYYY-MM-DD>
- Status: [STABLE | IN PROGRESS | BLOCKED | DEPRECATED | PLANNED]
- Built/Modified: <Exact absolute or repo-relative paths>
- Tested: <Exact command executed, test counts passed/failed, duration>
- Invariants & Deviations: <Key architectural choices or fallbacks used>
- Next Immediate Step: <Pointer to the exact next sub-phase/task>
```

### Rule 4: Contract Change Protocol
- Never modify [`instructions/Contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md) silently.
- If a schema change is needed: log the old vs new schema diff, affected modules, and backward-compatibility stance in Section 5.

### Rule 5: Turn-Conclusion Checklist
Before completing your response, verify:
- [ ] Code executed / tested via CLI or pytest.
- [ ] `scripts/preflight_check.py` or module diagnostics run.
- [ ] `git status` inspected — zero untracked stray files.
- [ ] `06_Memory.md` updated with the latest state.

---

## 2. Current System State & Active Focus

- **Current Timestamp**: 2026-09-09T18:27:00+05:30
- **System Health**: 100% Green (`scripts/preflight_check.py` verified)
- **Overall Status**: `MILESTONE 1 COMPLETE` | `MILESTONE 2 ACTIVE`
- **Active Milestone**: **Milestone 2 — Deployment-Level Testing, Module Web Testbed & Issue Resolution**
- **Immediate In-Flight Objectives**:
  - [ ] **Phase 10.4**: Implement ML Core CLI Diagnostics (`scripts/run_ml_core_diagnostics.py`).
  - [ ] **Phase 10.5**: Implement Backend REST/WS CLI Diagnostics (`scripts/run_backend_diagnostics.py`).
  - [ ] **Phase 11.1**: Build Unified Web Testbed (`modules/frontend/src/testbed.html`, `testbed.js`, `testbed.css`).
  - [ ] **Phase 11.2–11.6**: Wire Backend `/api/v1/testbed/` router for module-isolated browser testing.

---

## 3. Canonical Subsystem & File Map (Zero-Guesswork Index)

| Module | Core Source Files | Primary Classes | Contract (§) | Test / Diagnostic Command |
| :--- | :--- | :--- | :--- | :--- |
| **RAG** | `modules/rag/src/service.py`<br>`modules/rag/src/parsing/parser.py`<br>`modules/rag/src/retrieval/retriever.py` | `RAGService`<br>`parse_document`<br>`HybridRetriever` | §4, §14 | `pytest modules/rag/tests/` |
| **Avatar & Voice** | `modules/avatar_voice/src/services/avatar_voice_service.py`<br>`modules/avatar_voice/src/tts/edge_tts_adapter.py`<br>`modules/avatar_voice/src/avatar/viseme_generator.py`<br>`modules/avatar_voice/src/compositor/ffmpeg_compositor.py` | `AvatarVoiceService`<br>`TTSAdapter`<br>`VisemeGenerator`<br>`FFmpegCompositor` | §6, §7, §14 | `./.venv/bin/python scripts/run_avatar_voice_diagnostics.py`<br>`pytest modules/avatar_voice/tests/` |
| **Agent Orchestration** | `modules/ai_agent_orchestration/src/orchestration/teacher_orchestrator.py`<br>`modules/ai_agent_orchestration/src/agents/planner.py`<br>`modules/ai_agent_orchestration/src/agents/explainer.py`<br>`modules/ai_agent_orchestration/src/agents/questioner.py`<br>`modules/ai_agent_orchestration/src/agents/assessment.py` | `TeacherOrchestrator`<br>`PlannerAgent`<br>`ExplainerAgent`<br>`QuestionerAgent`<br>`AssessmentAgent` | §5, §8, §9, §10 | `./.venv/bin/python scripts/verify_live_gemini_quality.py`<br>`pytest modules/ai_agent_orchestration/tests/` |
| **ML Core** | `modules/ml_core/src/services/evaluation_service.py`<br>`modules/ml_core/src/evaluators/mcq_evaluator.py`<br>`modules/ml_core/src/evaluators/freeform_evaluator.py`<br>`modules/ml_core/src/taxonomy/misconception_classifier.py` | `EvaluationEngine`<br>`MCQEvaluator`<br>`FreeformEvaluator`<br>`MisconceptionClassifier` | §8, §9, §11 | `./.venv/bin/python scripts/run_ml_core_diagnostics.py`<br>`pytest modules/ml_core/tests/` |
| **Backend** | `modules/backend/src/main.py`<br>`modules/backend/src/api/v1/sessions.py`<br>`modules/backend/src/api/v1/materials.py`<br>`modules/backend/src/services/ai_operation_service.py` | `FastAPI app`<br>`AIOperationService`<br>`SessionManager` | §12, §13 | `./.venv/bin/python scripts/run_backend_diagnostics.py`<br>`pytest modules/backend/tests/` |
| **Frontend** | `modules/frontend/src/index.html`<br>`modules/frontend/src/classroom.html`<br>`modules/frontend/src/report.html`<br>`modules/frontend/src/testbed.html`<br>`modules/frontend/src/js/classroom.js` | Web Application Client UI | §12, §13 | Start server & open browser on `http://localhost:8000` |
| **Testing** | `scripts/preflight_check.py`<br>`scripts/run_live_demo.py`<br>`tests/integration/` | Full System Test Harness | All | `./.venv/bin/python scripts/preflight_check.py`<br>`pytest tests/` |

---

## 4. Common Execution Recipes

```bash
# 1. Complete Preflight Health Check (Always run first)
./.venv/bin/python scripts/preflight_check.py

# 2. Run Full Automated Unit & Integration Regression Suite
./.venv/bin/python -m pytest tests/ modules/*/tests/ -v

# 3. Launch Backend Server with Web Client
./.venv/bin/python -m uvicorn modules.backend.src.main:app --reload --host 0.0.0.0 --port 8000

# 4. Run Interactive Live Terminal Demo
./.venv/bin/python scripts/run_live_demo.py --topic "Photosynthesis" --language "en"
```

---

## 5. Architectural Invariants & Non-Negotiable Gotchas

1. **Runtime Prompts Guard**:
   - `modules/ai_agent_orchestration/src/prompts/*.md` (`assessment_system.md`, `explainer_system.md`, `planner_system.md`, `questioner_system.md`) are **dynamically loaded at runtime** by `self.load_prompt(...)`.
   - **NEVER move, rename, or delete these files.**
2. **PyTorch / HuggingFace Multi-threading**:
   - Always keep `TOKENIZERS_PARALLELISM=false` and `OMP_NUM_THREADS=1` in environment to prevent macOS/Windows fork crashes.
3. **Tiered Fallback Architecture**:
   - **Voice**: Edge-TTS cloud neural voices -> Local acoustic sine generator.
   - **Avatar**: 24 FPS visemes + FFmpeg 1080p compositor -> PIL canvas compositor.
   - **LLM**: Live Google Gemini (`gemini-1.5-flash`) -> Deterministic rule-based engines.
4. **Git Tree Invariant**:
   - All file operations must use `git mv` or `git rm`. Working tree must stay clean.

---

## 6. Phase Implementation Log & Chronological Memory

### [Milestone 1: Phases 0–9] Production Subsystem Build — COMPLETED (2026-09-08)
- **Phase 0 (Skeleton & Contracts)**: Pydantic v2 schemas locked per `Contract.md`. Resolved `ParsedDocument.warnings` serialization leak.
- **Phase 1 (Ingestion & Adapters)**: Parsers for PDF, DOCX, PPTX, TXT. Indic script and heading-preserving chunker. Upload REST endpoints in Backend.
- **Phase 2 (RAG & Planning)**: 1024-dim BGE-M3 embeddings, ChromaDB vector store, RRF hybrid retrieval with BGE cross-encoder reranker. Planner Agent generates structured `LessonNode` DAGs.
- **Phase 3 (Explainer & Visuals)**: Explainer Agent with grounded citation enforcement. Visual type suggester mapping content to 6 visual renderers (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`).
- **Phase 4 (Avatar, Voice & Compositor)**: 24 FPS Viseme-driven avatar, multilingual Edge-TTS audio with WebVTT timestamps, 1920x1080 FFmpeg compositor (70% visual canvas, 30% avatar PiP, bottom captions).
- **Phase 5 (Interaction Loop)**: Full-duplex WebSocket `/sessions/{id}/live` driver. Questioner Agent generates contextual formative assessment questions.
- **Phase 6 (Evaluation & Adaptation)**: Rule-based exact MCQ evaluator, Sentence-Transformers hybrid freeform scorer, 15-class physics misconception classifier. Adaptation Controller routes to `ALLOW`, `MODIFY`, or `REGENERATE`.
- **Phase 7 (Assessment & Backend)**: Assessment Agent generates diagnostic summary, Bloom taxonomy mastery radar, and persistent learner profile updates. FastAPI routes & WebSocket transport operational.
- **Phase 8 (Frontend Classroom)**: Full production web UI (`index.html`, `classroom.html`, `report.html`) with dual-mode upload (PDF/Topic), live video playback, teacher pose reactive avatar, and telemetry HUD.
- **Phase 9 (Docs, Restructure & Polish)**: Root decluttered (17 stray files cleaned). All specs moved to `docs/spec/`. Duplicates purged (`docs/archive/`, `docs/modules/`, `new_phases.md`, `docs/system/progress.md`, `setup_commands.md` removed). Synchronized `modules/ai_agent_orchestration/docs/ai_agent_orchestration_detail.md` to authoritative code level (all 18 Python source/agent/schema files and 34 passing unit/integration tests documented). Preflight check 100% green.

---

### [Milestone 2: Phases 10–13] Deployment Testing & Module Web Testbeds — ACTIVE

### [Phase 10] Module-Wise Diagnostic CLI Test Harnesses — 2026-09-08
- **Status**: IN PROGRESS
- **Built/Modified**:
  - `scripts/preflight_check.py` (Master environment & dependency integrity checker)
  - `scripts/run_rag_diagnostics.py` (Deep ingestion, vector retrieval, cross-encoder CLI diagnostics)
  - `scripts/run_avatar_voice_diagnostics.py` (Edge-TTS, Viseme 24 FPS, FFmpeg composition CLI harness)
  - `scripts/verify_live_gemini_quality.py` (Agent brain prompt evaluation with live Gemini API)
- **Tested**: `preflight_check.py` passes 100% green. 87 pytest unit tests passing.
- **Next Immediate Step**: Complete `scripts/run_ml_core_diagnostics.py` and `scripts/run_backend_diagnostics.py`.

### [Phase 11] Interactive Module Web Testbeds (Playground UIs & Loggers) — 2026-09-09
- **Status**: IN PROGRESS (Orchestration & RAG Complete)
- **Built/Modified**:
  - **Orchestration Module (Port 8001)**:
    - `modules/ai_agent_orchestration/tests/web_test/server.py` (FastAPI testbed on port 8001; 0 changes to `modules/backend/`).
    - `modules/ai_agent_orchestration/tests/web_test/logger.py` (Structured logger with `planner/`, `explainer/`, `questioner/`, `adaptation/`, `fsm/`, `errors/`).
    - `modules/ai_agent_orchestration/tests/web_test/static/` (Interactive UI & live log explorer).
    - `modules/ai_agent_orchestration/tests/unit/test_web_test_server.py` (7/7 unit tests passing; 41/41 suite green).
  - **RAG Module (Port 8002)**:
    - `modules/rag/docs/rag_detail.md` (Fully updated with complete structural file guide of all 21 Python source files and explicit Rule-Based vs Dynamic logic classifications).
    - `modules/rag/instructions/detail_plan.md` (Updated with Milestone 1 deliverables and Milestone 2 isolated testing architecture).
    - `modules/rag/instructions/overview.md` & `contract.md` (Updated reading sequences, schemas, and invariants).
    - `modules/rag/tests/web_test/server.py` (Isolated FastAPI test server on port 8002 directly importing `modules.rag.src.*`).
    - `modules/rag/tests/web_test/logger.py` (Hierarchical logger with `parsing/`, `chunking/`, `embedding/`, `indexing/`, `retrieval/`, `grounding/`, `errors/`).
    - `modules/rag/tests/web_test/static/` (`index.html`, `style.css`, `app.js` with **Light Professional theme** [no dark mode], drag & drop ingestion, Indic chunker analysis, hybrid retrieval, hallucination detection, and real-time log viewer).
    - `modules/rag/tests/unit/test_rag_web_test_server.py` (8/8 unit tests passing; full suite 26/26 green in 25.49s).
- **Tested**: 41/41 orchestrator tests + 26/26 RAG tests passing. Working tree clean.
- **Next Immediate Step**: Proceed to `modules/ml_core/` audit and testbed (Port 8003).
### [Phase 12] Deployment Stress Testing & Bug Resolution — PLANNED
- **Status**: PLANNED
- **Next Immediate Step**: Multi-page PDF stress testing, rate limit handling, and memory leak audit.

### [Phase 13] Production Certification & Official Demo Recording — PLANNED
- **Status**: PLANNED
- **Next Immediate Step**: 3–7 minute end-to-end classroom recording and submission sign-off.

### [Task Phase 1+2] Lesson length, chapter notes, board relevance — IMPLEMENTED
- **CCR-1 used**: `TeachingSegment.notes {key_points, example}` added as an *optional* field, so old payloads and the mock adapter stay valid. Contract otherwise untouched.
- **CCR-2 not needed**: a citation carrier already exists (`citation_updated` over WS, `lesson_service.record_citation`).
- **Already implemented before this pass, so skipped**: 1.D assessment (backend emits `assessment_report`, frontend redirects to `report.html` with real data), checkpoint gating (the question is only sent after the render completes), the hardcoded-biology-chip and AI-Inspector defects (they live in the old `tests/web_test` UI, not the production frontend).
- **Deferred**: 1.A richer provenance (page/section/risk badge) — retrieval returns plain strings, so chunk metadata would need a `rag_client` change; 2.D avatar PiP framing and the blue-badge hunt.
- **Needs live run**: video duration vs. target words, and the rendered boards in a real lesson — `HUMAN LIVE TEST REQUIRED`.

### [Task Phase 1+2 — pass 2] Provenance, notes store, email, Gemini call path
- **Gemini**: the key IS read and `GeminiLLMAdapter` is selected (verified, no live call made). Fixed in the call path: no `maxOutputTokens` was sent (long scripts could truncate), a reply with no parts fell through to SmartMock **silently** — it now logs `finishReason`; `last_error` could raise `NameError`; timeout 30s → 90s.
- **Provenance (1.A)**: `RAGClient.retrieve_detailed()` keeps chunk_id/page/section/score + `risk_level`; orchestrator stores it on the session; WS citation now carries file name, page/section, passage count and a grounding badge; weak context says "no matching document context" and sends no citation.
- **Duplicate transcript**: `.stage-caption` printed the whole script that the Chapter Notes card already showed. Element, CSS and JS writes removed.
- **Notes store**: new `lesson_nodes.notes_json` + additive `_add_missing_columns()` migration in `init_db` (create_all only makes missing *tables*), `GET /lessons/{id}/notes?format=json|markdown&download=true`, class-notes panel that survives a reload, and Download buttons in the classroom and on the report page.
- **Email**: credentials were in `.env` but `ENABLE_SMTP_SEND` defaulted False, so every mail went to `data/outbox/`. Unset now means "send if SMTP is configured"; SMTP login to Gmail verified. `EXPOSE_DEV_OTP` now defaults off once SMTP is configured — returning a live OTP in an API response is account takeover.
- **2.D**: viseme min-hold of 2 frames + mouth closes on silence; PiP bottom-anchored in a framed panel (filter graph verified with ffmpeg on synthetic inputs). No blue badge exists in the render pipeline — it must be an HTML overlay; not found, not removed.

### [instructions/task.md] Mentor escalation, adaptation UX, loading polish — IMPLEMENTED
- **T2/T3 mentor escalation**: `mentor_name`/`mentor_email` added directly to `User` (1:1, no join table — matches the doc's own "least invasive shape" guidance), migrated additively. Signup form, settings page, and account API all expose them. `EmailService.send_mentor_escalation()` reuses the existing SMTP/Resend transport; content is limited to this concept's question/answer/misconception/failure-count (no other student data, no secrets), HTML-escaped (student free-text answers were going into raw HTML unescaped). Idempotency via a `LessonEvent(event_type="mentor_notified", node_id=...)` row checked before sending — verified a second escalation call does not re-send. Failure is fully isolated: `_notify_mentor` catches everything and returns False; the WS `human_escalation` event and student-facing copy are identical either way.
- **T4 adaptation UX**: new `.adaptation-banner` component in classroom, mapped 1:1 to backend `action` (MODIFY/REGENERATE/HUMAN — ALLOW hides it), keyed by `node_id:action` so reconnects can't stack duplicates, cleared when the next `explanation_chunk` arrives, with a 20s "still working" fallback instead of hanging silently.
- **T5/T6 video quality**: already fixed in the earlier phase-1/2 pass (diagram placeholder fallback, board legibility, LaTeX sanitizer) — not re-touched.
- **T7/T8 (avatar gesture polish, multi-board segments)**: deferred — P2, time-boxed out; avatar PiP/lip-sync polish from the earlier pass stands as-is.
- **Loading UX** (user request, not in task.md): a brand-consistent `#page-loader` overlay inserted into all 13 HTML pages (min 380ms, independent of module-script timing so it can't hang), plus a CSS entrance animation on the landing hero and auth cards. Kept separate from classroom's existing connect/render overlays.
- **Needs live verification**: an actual mentor inbox receiving the email (SMTP/Resend still not configured on Render per earlier conversation — will log-fallback until that's set up) — `HUMAN LIVE TEST REQUIRED`.

### [Live log triage] Root cause of the generic teaching boards — FIXED
- `DiagramRenderer`/`Graph`/`Image`/`Map`/`Timeline` unwrapped `visual_spec` with
  `visual_spec.get("content") if isinstance(visual_spec, dict) else visual_spec` — but the pipeline
  passes a **Pydantic `VisualSpec`**, not a dict, so the whole object became `content`, no parse branch
  matched, and every board fell through to placeholder labels. Equation/Code already used `getattr` and
  were therefore fine. This — not prompt quality — is why "Input Data → Processing Engine" appeared.
  Fixed all five to `getattr(visual_spec, "content", visual_spec)`.
- Fixing it exposed two latent bugs on code paths that had never actually executed:
  `TimelineRenderer` crashed (`'str' object has no attribute 'get'`) because the dict branch passed
  `events` through unnormalised; `GraphRenderer` defaulted to a built-in 2,4,8…256 series, i.e. it drew
  a **fabricated exponential curve and presented it as the concept's real data** whenever the spec used
  any key other than x/y. Both now normalise the shapes models actually emit and fall back to an honest
  title card with a WARNING instead of inventing content.
- Diagram cards also now fill the board vertically (were using ~1/3 of it).
- Verified by rendering the exact `VisualSpec` from the live Render log; board shows the real lesson nodes.
- **Gemini key was leaking into logs**: the key was passed as `?key=...`, and httpx logs the full request
  URL at INFO, so every call wrote the secret into the server log (retained and readable on Render).
  Moved to the `x-goog-api-key` header; verified the URL no longer contains it.

### [task_agentic_ai_modernization.md] Phases 0,1,3,5,6 — IMPLEMENTED
- **Phase 0 audit corrected three plan assumptions** (`current_task/phase0_findings.md`):
  `mlops/src/` was *empty* (no PerfTrace to extend — it had to be built; only `rag/src/perf.py` existed);
  `learner_profiles` was *already fully implemented* incl. `refresh_learner_profile()`, so Phase 5's write
  side existed and only the read path was missing; and `lesson_events` already had the exact
  `{event_type, lesson_id(=session_id), node_id, payload, occurred_at}` shape, so **no `agent_events` table
  was needed**.
- **Phase 1 (trace)**: `modules/mlops/src/agent_trace.py` — process-wide tracer with a pluggable sink, so
  `rag`/`ai_agent_orchestration` emit without importing the backend. `_SENSITIVE_KEYS` strips prompts,
  scripts, raw answers and credentials *before* an event leaves the process; long values truncate. Backend
  installs the sink at startup → `lesson_events` with an `agent.` prefix; read via `GET /lessons/{id}/trace`
  (owner-scoped). Sink failure can never interrupt a lesson.
- **Phase 3 (agentic RAG)**: `RAGService.retrieve_context_agentic()` — retrieve → reuse the *existing*
  `has_sufficient_context` (0.52 threshold, no new threshold invented) → refine once → stop.
  **Refinement is deterministic** (content terms + topic, framing words like "Introduction" dropped), so the
  loop adds **no LLM call and no quota cost** — the plan had assumed an LLM refinement step. Always falls
  back to the single-pass result; topic-only mode never refined. `RetrievalResult.attempts/refined_query`
  are additive-optional.
- **Phase 5 (memory)**: `SessionManager.memory_for()` builds a narrow payload (strong/weak concepts,
  misconceptions seen >1×) from the existing table; orchestrator passes it to the Planner **in PLAN only**;
  `planner_system.md` gained the missing usage rules. Dead wiring closed: the planner had accepted
  `learner_profile` all along but nothing ever passed one.
- **Deferred per the plan's own §8 matrix**: Phase 2 (LangGraph, "Could Have" — heavyweight dep on a
  <512 MB deploy, highest-risk touch to working orchestration) and Phase 4 (MCP, listed "Future Scope" —
  adds an IPC boundary for no correctness gain). Phases 3/5 are plain bounded Python, which §8 permits.
- 285 tests pass (was 252). `Contract.md` unchanged; FSM state names and ADAPT semantics unchanged.

### [Agentic RAG A/B] Measured — single-pass vs bounded loop
Both paths kept live. `python -m modules.rag.tests.benchmark.compare_retrieval_modes` runs the existing
benchmark harness in both modes (`--suite`, `--json`). `AGENTIC_RAG_ENABLED=false` restores exact
single-pass behaviour in production (`max_refinements=0`).

Results over 24 queries, real BGE-M3 + Chroma, no LLM in the loop:

| Suite | Refined | Grounded rate | Risk accuracy | p50 latency |
|---|---|---|---|---|
| Physics NCERT (8) | 0/8 | 1.000 = | 1.000 = | −11% (noise) |
| Lesson-Node Concepts (8) | 0/8 | 1.000 = | 1.000 = (MRR 1.000 =) | −6% (noise) |
| Multilingual (4) | 2/4 | 0.500 = | 1.000 = | +55% |
| Cross-Domain Rejection (4) | 3/4 | 0.250 = | 0.750 = | +94% |

**Verdict: safe, but benefit unproven on this corpus.** 5 refinements fired, **0 rescues**. No quality or
safety regression anywhere — critically, refinement never turned an off-domain query into false
grounding. Cost is zero when the first pass already grounds (0 refinements on both physics suites) and
only materialises where retrieval had already failed.

The premise (verbose Planner node titles like "Introduction to…" weaken grounding) is **not supported**:
a new `lesson_nodes` suite using the real production query shape, with per-section ground truth,
retrieves 8/8 at MRR 1.000 single-pass. Refinement cannot help where nothing is broken. The two suites
where it did fire were unrescuable by design (off-domain, and Hindi transliteration — which needs
translation, not term extraction).

**Also found:** the three pre-existing suites ship `expected_chunk_ids=[]`, so their Precision/MRR/nDCG/
Recall were vacuous (0.0/1.0 by definition, not measurements). The comparison tool now prints `n/a` for
them instead of misleading numbers; only `lesson_nodes` has real ground truth.

Still needs a real uploaded document (messier than this clean synthetic chapter) to decide whether to
keep the loop on by default.

### [Agentic RAG A/B — final] Real uploaded PDF tested; verdict updated
Ran the one test that was still open: a PDF **actually uploaded through the app**
(`data/storage/daad.../8d99....pdf`, "Newton's Laws", 4 chunks) with genuine extraction noise —
content split mid-sentence across pages, section titles mis-detected as `"where:"`. New `real_pdf`
suite, 8 Planner-style node concepts, ground truth labelled from the chunks' actual text.
`BenchmarkDocument.source_path` now lets a suite benchmark a real file instead of inline prose.

Result: **single-pass grounds 8/8, MRR 0.854, nDCG 0.871, Recall 1.000 — the loop fired 0 times.**

Cumulative across 5 suites / 32 queries: **5 refinements, 0 rescues.** The loop is proven *harmless*
(zero cost on the happy path — 0 refinements across all 24 in-domain queries; no quality or safety
regression anywhere) and remains *unproven useful*. The real-PDF test I had flagged as the one case
that could still show a rescue came back negative, so the case for the loop is now weaker, not stronger.

**Standing recommendation: keep enabled** (`AGENTIC_RAG_ENABLED=true`, the default) — its cost is
confined to retrievals that have *already failed*, where the alternative is teaching the node
ungrounded, and ~600 ms to try once more is cheap insurance. Disable it if demo latency on the
no-context path ever matters. The one shape still untested is a document whose vocabulary genuinely
differs from the Planner's phrasing (e.g. a Hindi/Bengali textbook with English node titles) — the
synthetic case where a rescue *did* occur.

### [Production audit] Breakers found and fixed
Measured, not guessed. Four real issues; three fixed in code, one is an infra decision.

1. **OOM on first document upload (was: hard container kill).** Retrieval models load *lazily on first
   upload*, not at startup, so a small instance boots fine and dies when a learner uploads. Measured RSS:
   idle 53 MB → after ingest **2,426 MB** (BGE-M3) → after retrieval **3,786 MB** (+ cross-encoder). That
   is ~7× a 512 MB free tier. This is why the live logs only ever showed *topic* lessons — without a
   `document_id` retrieval short-circuits and the models never load.
   *Fixed:* `EMBEDDING_BACKEND` / `EMBEDDING_MODEL` / `EMBEDDING_DEVICE` / `RERANKER_MODEL` /
   `RERANKER_ENABLED` are now env-driven (were hardcoded constructor defaults), so a small host can pick
   a MiniLM-sized model and skip the cross-encoder (falls back to the existing lexical-overlap path).
   Startup prints the memory requirement in production.

2. **Silent fabricated grounding.** Both embedding adapters fall back to deterministic *hash* vectors when
   the model can't load (blocked download, missing dep). Similarity over those is meaningless, but the
   scores still look like scores, so retrieval reported `has_sufficient_context=True`, `risk_level="low"`
   and the classroom would cite a learner's document for content it never matched.
   *Fixed:* adapters expose `is_degraded`; `RAGService._guard_degraded_embeddings()` forces
   `has_sufficient_context=False` / `high_hallucination_risk` / no chunks, logging once. Upload now marks
   such a document `failed` with an actionable message instead of leaving it "ready" but unusable.

3. **Upload froze the whole server.** `upload_document` is `async def` but called blocking
   `ingest_document` (model load + embedding) directly, blocking the event loop — on a single worker that
   halts every other request, all classroom WebSockets and the host health check, long enough on a first
   upload for the platform to restart the container mid-lesson. Demonstrated: 0 heartbeats served during a
   1.5 s upload before, 15 after. *Fixed:* runs via `run_in_executor`. Swept the rest of the codebase —
   this was the only `async def` endpoint with the bug; `ws.py` already used executors and every other
   route is sync `def` (FastAPI threadpools those).

4. **All state is ephemeral — NOT fixable in code (infra decision).** DB, uploads, rendered media and the
   Chroma index all live under `data/` on the container filesystem, and `_resolve_sqlite_path()` **rejects
   Postgres** (`Only sqlite:/// URLs are supported`). On Render free tier every deploy/restart wipes
   accounts, lessons and uploads. Needs either a mounted persistent disk (paid instance) or Postgres
   support added. Startup now warns loudly in production.

291 tests pass (was 285). Nothing committed.

### [Phase 2 — LangGraph] IMPLEMENTED (previously deferred)
Built after re-checking my own reasoning for deferring it. **One of my two stated reasons was wrong:**
langgraph is ~5.8 MB, not a "heavyweight dependency" — the 2.4 GB memory problem was BGE-M3, a
different thing entirely. The real cost is ~20 transitive packages (langchain-core, langsmith, httpx2)
and a silent `websockets` downgrade 17.1 → 16.1.1 (verified: full suite green and a live WS handshake
against the classroom route still works).

`src/state_machine/langgraph_adapter.py`: graph topology mirrors `VALID_TRANSITIONS`; node bodies
delegate to the existing `TeacherOrchestrator` so all agent logic is reused verbatim; edges are
deterministic functions of the returned `TeacherState` (no prompt-driven routing, per §4.1.G);
`SessionState`/SQLite stay authoritative with the graph holding routing data only (§4.1.D). Exposes the
same `step()` signature, so the WS loop and service layer are untouched. The classroom drives the loop
externally (it renders video and waits for the learner between steps), so the graph is stepped one node
per call rather than run to completion.

Selected by `ORCHESTRATION_RUNTIME=langgraph`; **default stays `fsm`**, and it falls back to the
dispatcher if the optional dep is missing, so a deploy can't be bricked.

**Parity test caught a real bug in my own adapter:** `__getattr__` forwarded reads but not writes, so
`orchestrator.ml_core = client` landed on the wrapper while execution used the inner object — silently
ignored but looking successful. Added `__setattr__` forwarding.

302 tests pass under **both** runtimes (`ORCHESTRATION_RUNTIME=fsm` and `=langgraph`).

Honest value note: the plan (§4.1) cites checkpointing, state streaming and HITL interrupt as
LangGraph's selling points — this project already hand-rolls all three and they work (SQLite resume, WS
streaming, HUMAN branch). So functionally this buys close to nothing; its value is legibility and the
demo narrative. It is safe because the original dispatcher remains the default and parity is enforced.
