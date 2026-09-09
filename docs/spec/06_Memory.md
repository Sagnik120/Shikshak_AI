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
| **RAG** | `modules/rag/src/services/rag_service.py`<br>`modules/rag/src/parsers/document_parser.py`<br>`modules/rag/src/retrieval/hybrid_retriever.py` | `RAGService`<br>`DocumentParser`<br>`HybridRetriever` | §1, §2, §3, §4 | `./.venv/bin/python scripts/run_rag_diagnostics.py`<br>`pytest modules/rag/tests/` |
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

### [Phase 11] Interactive Module Web Testbed (Playground UI) — 2026-09-09
- **Status**: IN PROGRESS
- **Built/Modified**:
  - `modules/ai_agent_orchestration/tests/web_test/server.py` (Dedicated isolated FastAPI test server on port 8001; zero changes to `modules/backend/`).
  - `modules/ai_agent_orchestration/tests/web_test/logger.py` (Structured execution trace logger writing to `logs/planner/`, `logs/explainer/`, `logs/questioner/`, `logs/adaptation/`, `logs/fsm/`, `logs/errors/`).
  - `modules/ai_agent_orchestration/tests/web_test/static/` (`index.html`, `style.css`, `app.js` with 6 interactive tabs and live log explorer).
  - `modules/ai_agent_orchestration/instructions/detail_plan.md` (Updated with Milestone 1 architecture completion and Milestone 2 testing & logging specifications).
  - `modules/ai_agent_orchestration/tests/unit/test_web_test_server.py` (7/7 unit tests verifying testbed server and logging engine).
- **Tested**: 41/41 orchestrator tests passing (0.97s). Preflight check 100% green.
- **Next Immediate Step**: Proceed to other module testbeds (RAG, ML Core, Avatar/Voice).

### [Phase 12] Deployment Stress Testing & Bug Resolution — PLANNED
- **Status**: PLANNED
- **Next Immediate Step**: Multi-page PDF stress testing, rate limit handling, and memory leak audit.

### [Phase 13] Production Certification & Official Demo Recording — PLANNED
- **Status**: PLANNED
- **Next Immediate Step**: 3–7 minute end-to-end classroom recording and submission sign-off.
