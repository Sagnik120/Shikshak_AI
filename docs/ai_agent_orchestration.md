# AI Agent Orchestration - Implementation Documentation

## 1. Module Purpose
The `ai_agent_orchestration` module acts as the central multi-agent pedagogical brain of Shikshak AI. It manages the teaching loop as an explicit finite-state machine (FSM), coordinating multiple specialized LLM agents (Planner, Explainer, Questioner, Assessor) and routing student responses to ML Core to determine pedagogical adaptations (e.g., re-explaining, progressing, or escalating).

## 2. File Structure
```
modules/ai_agent_orchestration/src/
├── adapters/
│   └── llm_adapter.py              # Facade for LLM interactions with JSON repair
├── agents/
│   ├── base.py                     # Base LLMAgent class
│   ├── planner.py                  # Generates LessonPlans
│   ├── explainer.py                # Generates TeachingSegments
│   ├── questioner.py               # Generates InteractionEvents
│   ├── assessment.py               # Generates AssessmentReports
│   └── adaptation_controller.py    # Determines ALLOW/MODIFY/REGENERATE
├── integration/
│   ├── ml_core_client.py           # Stub interface for ml_core Evaluators
│   └── rag_client.py               # Stub interface for RAG Context Retrieval
├── schemas/
│   ├── interaction.py              # StudentResponse, InteractionEvent
│   ├── lesson.py                   # LessonPlan, LearnerConstraints
│   ├── teaching.py                 # TeachingSegment, RenderedVideoSegment
│   └── evaluation.py               # EvaluationResult, AdaptationDecision
├── state_machine/
│   ├── orchestrator.py             # TeacherOrchestrator FSM execution
│   ├── session_state.py            # FSM state data container
│   ├── state_enum.py               # PLAN, EXPLAIN, ASK, EVALUATE, ADAPT
│   └── transitions.py              # FSM valid transition rules
├── service.py                      # Public TeacherOrchestrationService facade
└── logging_utils.py                # Structured logger
```

## 3. Core Agents & Prompts

### Planner Agent (`agents/planner.py`)
- **Inputs**: `ParsedDocument` or topic, `LearnerConstraints`.
- **Outputs**: `LessonPlan`.
- **Decision Logic**: Prompts the LLM to outline pedagogical nodes matching the time budget.

### Explainer Agent (`agents/explainer.py`)
- **Inputs**: Lesson node concept, grounded context (from RAG).
- **Outputs**: `TeachingSegment`.
- **Handling**: Binds RAG outputs into the prompt. Output specifies `visual_spec` and `avatar_cue`.

### Questioner Agent (`agents/questioner.py`)
- **Inputs**: `TeachingSegment` context.
- **Outputs**: `InteractionEvent` (MCQ or short answer).
- **Handling**: Ensures the question directly evaluates the concept just taught.

### Adaptation Controller (`agents/adaptation_controller.py`)
- **Inputs**: `EvaluationResult` (from ML Core).
- **Outputs**: `AdaptationDecision`.
- **Failure Threshold Logic**:
  - `correct=True` → `ALLOW`.
  - 1st Failure (Partial/Incorrect) → `MODIFY` (re-explain with new analogy).
  - 2nd Consecutive Failure → `REGENERATE` (abandon node, replan).
  - 3rd Consecutive Failure (after regeneration) → `HUMAN` (escalate).

### Assessment Agent (`agents/assessment.py`)
- **Inputs**: Complete session history of evaluations.
- **Outputs**: `AssessmentReport` identifying strong/weak concepts.

## 4. Finite State Machine (FSM)
Implemented in `state_machine/orchestrator.py`.
- **States**: `PLAN`, `EXPLAIN`, `ASK`, `EVALUATE`, `ADAPT`, `END`.
- **Flow**: `PLAN` → `EXPLAIN` → `ASK` → `EVALUATE` → `ADAPT`. 
- **Adaptation Routing**: Based on `ADAPT`, it routes back to `EXPLAIN` (if MODIFY) or `PLAN` (if REGENERATE) or next node (`EXPLAIN`).
- **Transitions**: Strictly validated in `transitions.py` to prevent illegal jumps (e.g. `ASK` to `PLAN`).

## 5. Integration Boundaries
- **RAG**: Consumes grounded contexts via `integration/rag_client.py`.
- **ML Core**: Sends student responses and receives `EvaluationResult` via `integration/ml_core_client.py`.
- **Avatar/Voice**: Outputs `TeachingSegment` intended for AvatarVoiceService.
- **Contract Adherence**: Uses `pydantic` schemas mirroring `instructions/Contract.md` perfectly.

## 6. Testing
- **Structure**: `tests/unit/` for agents/FSM logic. `tests/integration/` for pipeline/boundary stubs.
- **Tests passing**: 27/27 tests.
- **Dependencies**: Uses `FakeLLMAdapter` extensively to mock LLM network calls, ensuring deterministic testing.

## 7. Known Limitations
- The integration with Backend/Frontend is missing, so end-to-end sessions cannot currently be run outside of test fixtures.
- Personalization constraints (e.g., beginner/advanced) are currently passed through but are not explicitly enforced by a deterministic token-budgeting system.
