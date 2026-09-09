# detail_plan.md — ai_agent_orchestration

## Goal
Implement and verify the actual "teacher" as an explicit multi-stage agent and finite-state machine (FSM) — this is the highest-weighted rubric area (20 pts directly + heavily influences AI/ML 15 pts). Must NOT be a single "answer this question" prompt.

---

## 1. Subsystem Architecture (Completed in Milestone 1)

### The 5 Specialized Agents
1. **Planner Agent (`PlannerAgent`)** — input: `ParsedDocument` (optional) + `topic` (optional) + `LearnerConstraints` + `LearnerProfile` → output: `LessonPlan` (Contract §5).
   - Time budget compliance:
     - 5 min: 1–2 nodes, key concepts only, immediate summary.
     - 20 min: 3–5 nodes, structured theory with examples and 1 checkpoint question.
     - 60 min: 6–10 nodes, deep theory, multiple checkpoint questions, interactive exercises.
     - Multi-day: Grouped into sequential daily sub-plans.
2. **Explainer Agent (`ExplainerAgent`)** — input: single `LessonNode` + optional grounding chunks from `rag` + optional previous feedback → output: `TeachingSegment` (Contract §6).
   - Enforces grounding context (zero hallucination).
   - Selects visual type (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`) and avatar cue (`neutral`, `emphasis`, `questioning`).
   - On `MODIFY` loops: Mandates a brand new real-world analogy and visual aid without verbatim repetition.
3. **Questioner Agent (`QuestionerAgent`)** — input: `LessonNode` (where `checkpoint_question: true`) + recent teaching segment → output: `InteractionEvent` (Contract §8).
   - Varies question modality dynamically (`mcq`, `short_answer`, `problem`, `application`, `explain_in_own_words`).
   - Clears `options` list for non-MCQ question types.
4. **Adaptation Controller (`AdaptationController`)** — input: `EvaluationResult` + session evaluation history → output: `AdaptationDecision` (Contract §11).
   - `correct` → `ALLOW` (advance to next node).
   - `partial_credit` (> 0) or `misconception_tag` → `MODIFY` (re-explain with new analogy targeting misconception).
   - 1st failure → `MODIFY`.
   - 2nd consecutive failure on same node → `REGENERATE` (re-plan segment at lower foundational depth).
   - $\ge 3$ consecutive failures → `HUMAN` (escalate to human educator).
5. **Assessment Agent (`AssessmentAgent`)** — input: cumulative session `EvaluationResult` history → output: `AssessmentReport` (Contract §12).
   - Synthesizes `score_pct`, `strong_areas`, `weak_areas`, `recommended_next`, and personalized narrative feedback.

### Orchestration & State Machine
- Coordinated by `TeacherOrchestrator` across 10 explicit states:
  `UNDERSTAND -> PLAN -> EXPLAIN -> DEMONSTRATE -> QUESTION -> EVALUATE -> ADAPT -> CONTINUE -> DONE -> HUMAN_ESCALATION`.
- `AIOperationService` exposes session lifecycle and step execution methods.
- Telemetry emitted via `log_transition()` in `logging_utils.py`.

### LLM Adapters
- `GeminiLLMAdapter`: Production adapter connecting to Google Gemini REST API (`gemini-2.0-flash` / `gemini-1.5-flash`) via `httpx`, enforcing JSON output mode.
- `SmartMockLLMAdapter`: Deterministic context-aware mock adapter for offline testing and automatic fallback on network errors.

---

## 2. Milestone 2: Isolated Interactive Web Testbed & Structured Logging

### Purpose & Isolation Principle
- **Zero Production Disruption**: `modules/backend/` is NOT modified or polluted with test code.
- **Dedicated Test Server**: Testbed runs independently on `http://localhost:8001` via `modules/ai_agent_orchestration/tests/web_test/server.py`.
- **Single Source of Truth**: The test server directly imports and exercises production classes from `modules.ai_agent_orchestration.src.*`. Any enhancements or bug fixes apply directly to `src/`, benefiting the full application.

### Interactive Web Testbed Features (`tests/web_test/static/`)
1. **Curriculum Planner Tab**: Test arbitrary topic/document inputs, time budgets, and level settings to visually inspect the resulting `LessonPlan` node graph.
2. **Concept Explainer Tab**: Test single-node explanation generation, visual type selection, grounding chunks, and `MODIFY` analogy swapping.
3. **Questioner Tab**: Verify question modality variety and distractor formulation.
4. **Adaptation Controller Tab**: Test rule matrix transitions (`ALLOW`, `MODIFY`, `REGENERATE`, `HUMAN`) with simulated score and misconception inputs.
5. **FSM Step Simulator Tab**: Step through the complete 10-state lifecycle interactively.
6. **Live Log & Trace Explorer Tab**: In-browser view of recent execution traces and error logs.

### Structured Execution Logging Engine (`tests/web_test/logger.py`)
- Writes granular per-input, per-file, and per-function execution records into organized subdirectories:
  - `tests/web_test/logs/planner/`
  - `tests/web_test/logs/explainer/`
  - `tests/web_test/logs/questioner/`
  - `tests/web_test/logs/adaptation/`
  - `tests/web_test/logs/assessment/`
  - `tests/web_test/logs/fsm/`
  - `tests/web_test/logs/errors/`
- For each execution, records:
  - `run_id`, `timestamp`, `duration_ms`, `action`, `status`.
  - `inputs`: Full user request payload.
  - `trace`: Sequence of checkpoint dictionaries (`file`, `function`, `step`, `status`).
  - `llm_prompt`: System prompt and user prompt.
  - `llm_raw_response`: Raw string returned by model/adapter.
  - `output`: Validated Pydantic schema dictionary.
  - `error`: Complete exception message, traceback, file, and line number if an error occurs.
