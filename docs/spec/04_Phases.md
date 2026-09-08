# 04_Phases.md — Sequential Build Phases

> Each phase is dependency-ordered. Do not start Phase N+1 work in a given module before that
> module's Phase N exit criteria pass.

## Phase 0 — Skeleton
- Scaffold repo per `08_Folder_Structure.md`.
- Stub each module's API contract (empty FastAPI routers / stub functions matching
  `instructions/Contract.md` signatures) so modules can be developed in parallel against
  mocked responses.
- Exit: `run_all_diagnostics.py` runs (even if all checks are "not implemented") with no import errors.

## Phase 1 — Adapters & Ingestion
- `rag`: file parsers for PDF/DOCX/PPTX/notes → `ParsedDocument`.
- `backend`: upload endpoint, session creation, `LearnerProfile` CRUD (in-memory or Postgres).
- Exit: uploading a sample PDF returns a valid `ParsedDocument` JSON matching contract.

## Phase 2 — Core Components (Planning & Retrieval)
- `rag`: chunking + embedding + vector index + retrieval function with citation metadata.
- `ai_agent_orchestration`: Planner agent produces a `LessonPlan` from either a `ParsedDocument`
  retrieval context or a bare topic string, respecting level/time/language constraints.
- Exit: given a sample doc + "beginner, 20 min, Hindi", a valid `LessonPlan` JSON is produced.

## Phase 3 — Explanation & Visual Selection
- `ai_agent_orchestration`: Explainer agent turns each `LessonNode` into a `TeachingSegment`
  (script + visual_spec), subject-aware (math→equations/graphs, physics→diagrams/sim,
  programming→code/flow, history→timeline/map, biology→labeled diagram).
- `ml_core`: visual-type classifier/heuristic backing the visual_spec selection.
- Exit: every `LessonNode` maps to a non-generic `visual_spec`.

## Phase 4 — Video Generation
- `avatar_voice`: TTS (multilingual) + avatar rendering + on-screen visual compositing →
  `RenderedVideoSegment`.
- Exit: a `TeachingSegment` renders to a playable video file with audio+avatar+at least one
  on-screen visual element (not just avatar + subtitles).

## Phase 5 — Interaction Loop
- `ai_agent_orchestration`: Questioner agent emits `InteractionEvent`s at planned checkpoints.
- `frontend`: renders question UI (MCQ/short-answer), captures `StudentResponse`.
- `backend`: WebSocket turn handling between frontend and orchestration.
- Exit: a scripted demo session pauses for a question and accepts an answer.

## Phase 6 — Evaluation, Misconception Detection & Adaptation
- `ml_core`: `EvaluationResult` incl. misconception tagging (rule+LLM hybrid).
- `ai_agent_orchestration`: Adaptation Controller maps `EvaluationResult` →
  `AdaptationDecision` (ALLOW/MODIFY/REGENERATE/HUMAN) and loops back into Phase 3.
- Exit: an intentionally wrong answer triggers a *different* re-explanation (not a repeat).

## Phase 7 — Assessment, Reporting & Learner Profile
- Final quiz generation, `AssessmentReport`, persist to `LearnerProfile`, "recommended next"
  logic (from PS section 15's learning-path idea).
- Exit: end-to-end run produces a human-readable report matching the PS example format.

## Phase 8 — Frontend Polish & Multilingual Pass
- Full lesson player UI, language switch mid-session (context preserved), learner dashboard.
- Exit: switching language mid-lesson keeps the same `LessonPlan`/progress state.

## Phase 9 — Documentation & Demo Polish
- Fill `docs/` deliverables (architecture, models used, RAG approach, limitations, setup).
- Record 3–7 min demo video following: Upload/Topic → Lesson Planning → AI Teaching Video →
  Interaction → Adaptation → Assessment → Feedback.
- Exit: submission checklist in `09_Progress_Tracker.md` fully checked.
