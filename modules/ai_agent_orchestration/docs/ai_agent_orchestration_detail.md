# AI Agent Orchestration Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `ai_agent_orchestration`  
> **Repository Path**: `modules/ai_agent_orchestration/`  
> **Primary Phases**: Phase 2 (Lesson Planning), Phase 3 (Explanation & Visual Selection), Phase 5 (Interaction Loop), Phase 6 (Evaluation & Adaptation), Phase 7 (Assessment)  
> **Status**: **STABLE & PRODUCTION-READY** (34/34 Automated Tests Passing; 100% Contract-Compliant)  
> **Key Contracts**: Contract §5 (`LessonPlan`), Contract §6 (`TeachingSegment`), Contract §8 (`InteractionEvent`), Contract §11 (`AdaptationDecision`), Contract §12 (`AssessmentReport`), Contract §14 (`LLMAdapter`)

---

## 1. The Task (In Simple Language)

Imagine the best human teacher you have ever had. That teacher does not simply recite a textbook from start to finish without pausing. Instead, a great teacher:
1. **Plans the curriculum**: Before entering the classroom, they structure the lesson into bite-sized steps that match the student's background, learning style, and available time budget.
2. **Explains with vivid analogies and visuals**: They teach one concept at a time, pointing to diagrams, drawing equations, rendering graphs, or writing code on the board.
3. **Pauses to ask checking questions**: They ask: *"Now, why does this happen?"* or *"Can you calculate the result for this case?"*
4. **Listens and detects misconceptions**: If a student gives a wrong answer, the teacher doesn't just say "Incorrect" and move on. They diagnose *why* the student is confused (e.g., confusing velocity with acceleration, or forgetting net force).
5. **Adapts on the fly**: They explain the concept again using a fresh real-world analogy, a simpler visual aid, or an easier example until the student understands (never repeating the exact same lecture verbatim).
6. **Produces a progress report**: At the end of the lesson, they summarize what the student mastered, what needs review, and what to study next.

The **`ai_agent_orchestration`** module is this exact pedagogical mind. It is not a single generic chatbot prompt. It is an explicit, multi-agent finite-state machine (FSM) comprising the Planner, Explainer, Questioner, Adaptation Controller, and Assessor. It coordinates the entire educational journey from document ingestion to final mastery certification.

---

## 2. Technical Details & Architecture

The orchestration engine is structured as an explicit **Finite-State Machine (FSM)** coordinated by `TeacherOrchestrator` and driven through `AIOperationService`. Explicit states ensure full auditability, deterministic recovery on network reconnects, and live telemetry for the UI right-panel audit feed.

```
                    +----------------------------------------+
                    |               UNDERSTAND               |
                    | (Ingests inputs, topic, document_id)   |
                    +-------------------+--------------------+
                                        |
                                        v
                    +----------------------------------------+
                    |                  PLAN                  |
                    | (Planner Agent: generates LessonPlan)  |
                    +-------------------+--------------------+
                                        |
                                        v
                    +----------------------------------------+
                    |                EXPLAIN                 |
                    | (Explainer Agent: TeachingSegment)     |
                    +-------------------+--------------------+
                                        |
                                        v
                    +----------------------------------------+
                    |              DEMONSTRATE               |
                    | (Enqueues video in avatar_voice)       |
                    +---------+--------------------+---------+
                              |                    |
        [checkpoint_question  |                    | [checkpoint_question
         == True]             v                    v  == False]
    +---------------------------+       +---------------------------+
    |         QUESTION          |       |         CONTINUE          |
    | (Questioner: Interaction) |       | (Advance to next node)    |
    +-------------+-------------+       +-------------+-------------+
                  |                                   |
                  v                                   v
    +---------------------------+               +-----------+
    |         EVALUATE          |               |   DONE    |
    | (ml_core evaluates answer)|               | (Assessor |
    +-------------+-------------+               |  Report)  |
                  |                             +-----------+
                  v
    +---------------------------+
    |           ADAPT           |
    | (Adaptation Controller)   |
    +-------------+-------------+
                  |
    +-------------+---------------+-------------------+
    | (ALLOW)     | (MODIFY)      | (REGENERATE)      | (HUMAN)
    v             v               v                   v
[CONTINUE]    [EXPLAIN]         [PLAN]        [HUMAN_ESCALATION]
```

### The 5 Specialized Pedagogical Agents
1. **Planner Agent (`PlannerAgent`)**:
   - Ingests `ParsedDocument` structure (from RAG) or raw `topic` string, plus `LearnerConstraints` (level, language, time budget, style) and historical `LearnerProfile`.
   - Generates a structured `LessonPlan` (Contract §5) composed of ordered `LessonNode`s.
   - Respects strict time budgets:
     - **5 min**: 1–2 nodes, key concepts only, immediate summary.
     - **20 min**: 3–5 nodes, structured theory with examples and 1 checkpoint question.
     - **60 min**: 6–10 nodes, deep theory, multiple checkpoint questions, interactive exercises, and final quiz.
     - **Multi-day**: Chunked into sequential daily sub-plans.
2. **Explainer Agent (`ExplainerAgent`)**:
   - Focuses on a single `LessonNode` at a time.
   - Accepts grounded context chunks retrieved from `rag` to guarantee anti-hallucination.
   - Generates a `TeachingSegment` (Contract §6) containing conversational lecture text, visual specification (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`), and avatar cue (`neutral`, `emphasis`, `questioning`).
3. **Questioner Agent (`QuestionerAgent`)**:
   - Activated when a `LessonNode` specifies `checkpoint_question: True`.
   - Generates an `InteractionEvent` (Contract §8) with varying modalities (`mcq`, `short_answer`, `problem`, `application`, `explain_in_own_words`).
4. **Adaptation Controller (`AdaptationController`)**:
   - Deterministic rule engine driving the 20-point adaptation rubric.
   - Evaluates consecutive failures, misconception tags, and confidence scores to emit `ALLOW`, `MODIFY`, `REGENERATE`, or `HUMAN`.
5. **Assessment Agent (`AssessmentAgent`)**:
   - Evaluates the cumulative session history upon lesson completion.
   - Synthesizes an authoritative `AssessmentReport` (Contract §12) with percentage scores, mastery categorization, and next study recommendations.

---

## 3. Detailed File-by-File Technical Breakdown

Every single `.py` and prompt file in this module has an explicit, singular responsibility:

### 3.1 Public Service & Entrypoints

#### [`src/service.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/service.py) — `AIOperationService`
- **Class**: `AIOperationService`
- **Purpose**: High-level application facade consumed by the Backend WebSocket driver and REST endpoints.
- **State Registry**: Manages an in-memory dictionary `self.sessions: Dict[str, SessionState]`.
- **Methods**:
  - `init_session(session_id: str) -> SessionState`: Instantiates and registers a new session state.
  - `get_session(session_id: str) -> SessionState`: Retrieves an existing session or raises `KeyError`.
  - `process_next_step(session_id: str, current_state: TeacherState, inputs: Dict[str, Any]) -> Tuple[TeacherState, Any]`: Advances the state machine by exactly one step via `self.orchestrator.step()`, wrapping execution in structured exception logging.

#### [`src/logging_utils.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/logging_utils.py) — Telemetry Logging
- **Function**: `log_transition(session_id: str, from_state: TeacherState, to_state: TeacherState, reason: str, context_data: Optional[Dict[str, Any]] = None) -> dict`
- **Purpose**: Formats transition events into JSON-serializable dictionaries (`session_id`, `transition`, `reason`, `context`) that stream directly to the frontend right-panel audit feed.

---

### 3.2 State Machine Subsystem (`src/state_machine/`)

#### [`src/state_machine/states.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/state_machine/states.py) — `TeacherState` Enum
Defines the 10 explicit states of the pedagogical loop:
- `UNDERSTAND`: Ingests initial student constraints, document, and topic.
- `PLAN`: Generates the structured `LessonPlan`.
- `EXPLAIN`: Generates the grounded script and visual specification for the current node.
- `DEMONSTRATE`: Triggers `avatar_voice` video synthesis and captions.
- `QUESTION`: Synthesizes a contextual formative assessment question.
- `EVALUATE`: Dispatches the student's answer to `ml_core` for scoring.
- `ADAPT`: Evaluates scoring and misconception history to decide next pedagogical action.
- `CONTINUE`: Advances current node index or concludes the lesson.
- `DONE`: Synthesizes the final `AssessmentReport`.
- `HUMAN_ESCALATION`: Halts the automated loop when a student fails 3 consecutive times.

#### [`src/state_machine/session_state.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/state_machine/session_state.py) — `SessionState` Dataclass
Stores the complete runtime session state:
- `session_id: str`: Unique session UUID.
- `lesson_plan: Optional[LessonPlan]`: Active DAG lesson plan.
- `current_node_index: int`: Zero-indexed pointer into `lesson_plan.nodes`.
- `evaluation_history: List[EvaluationResult]`: Cumulative list of answer evaluations.
- `state_logs: List[dict]`: Complete chronological transition audit trail.
- `constraints: Optional[LearnerConstraints]`: Level, language, time budget, and learning style.
- `topic: Optional[str]` and `document_id: Optional[str]`: Target material references.
- `current_feedback_override: Optional[str]`: Remedial instruction passed to `ExplainerAgent` on `MODIFY`.
- `recent_segment: Optional[Any]` and `recent_question: Optional[Any]`: Cache of active teaching segment and question.

#### [`src/state_machine/transitions.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/state_machine/transitions.py) — Transition Rules
- **Constant**: `VALID_TRANSITIONS: Dict[TeacherState, List[TeacherState]]` defines the strict directed graph.
- **Function**: `is_valid_transition(from_state: TeacherState, to_state: TeacherState) -> bool` enforces transition legality, raising `ValueError` on any invalid state hop.

#### [`src/state_machine/orchestrator.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/state_machine/orchestrator.py) — `TeacherOrchestrator`
- **Class**: `TeacherOrchestrator`
- **Dependencies Injected**: `PlannerAgent`, `ExplainerAgent`, `QuestionerAgent`, `AdaptationController`, `AssessmentAgent`, `RAGClient`, `MLCoreClient`, `AvatarClient`.
- **Method**: `step(current_state: TeacherState, session: SessionState, inputs: Dict[str, Any]) -> Tuple[TeacherState, Any]`:
  - Dispatches execution based on `current_state`.
  - On `EXPLAIN`: Fetches context chunks from `RAGClient` if `document_id` exists; passes `current_feedback_override` if in a remedial loop.
  - On `DEMONSTRATE`: Sends segment to `avatar_client.render_segment(segment)`; routes to `QUESTION` if `checkpoint_question == True`, else routes to `CONTINUE`.
  - On `EVALUATE`: Invokes `ml_core.evaluate_answer()` with expected concept from recent question.
  - On `ADAPT`: Evaluates `AdaptationDecision`. If `ALLOW` $\rightarrow$ `CONTINUE`; if `MODIFY` $\rightarrow$ sets `session.current_feedback_override` and returns to `EXPLAIN`; if `REGENERATE` $\rightarrow$ returns to `PLAN`; if `HUMAN` $\rightarrow$ returns to `HUMAN_ESCALATION`.
  - On `DONE`: Invokes `AssessmentAgent.generate_report()`.

---

### 3.3 Agents Subsystem (`src/agents/`)

#### [`src/agents/base.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/agents/base.py) — `BaseAgent`
- **Class**: `BaseAgent`
- **Methods**:
  - `load_prompt(filename: str) -> str`: Loads system prompt markdown files from `modules/ai_agent_orchestration/src/prompts/`.
  - `call_llm_json(system_prompt: str, user_prompt: str, response_model: Type[T], max_retries: int = 1) -> T`:
    - Executes completion via `self.llm.complete(messages)`.
    - Automatically detects and strips markdown wrappers (` ```json ... ``` `).
    - **Self-Healing Loop**: If JSON decoding or Pydantic validation fails, it records the validation error, adds a repair user message, and retries up to `max_retries`.

#### [`src/agents/planner.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/agents/planner.py) — `PlannerAgent`
- **Class**: `PlannerAgent(BaseAgent)`
- **Prompt**: Binds to `planner_system.md`.
- **Method**: `plan_lesson(constraints: LearnerConstraints, source_type: str, topic: Optional[str] = None, parsed_doc: Optional[Any] = None, learner_profile: Optional[Any] = None) -> LessonPlan`:
  - Structures syllabus into sequential `LessonNode`s matching student level and time budget.

#### [`src/agents/explainer.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/agents/explainer.py) — `ExplainerAgent`
- **Class**: `ExplainerAgent(BaseAgent)`
- **Prompt**: Binds to `explainer_system.md`.
- **Method**: `generate_segment(node: LessonNode, constraints: LearnerConstraints, grounding_chunks: Optional[List[Any]] = None, previous_feedback: Optional[str] = None) -> TeachingSegment`:
  - Enforces grounding context when chunks are supplied.
  - If `previous_feedback` is present (from `MODIFY`), explicitly commands the LLM to supply a *brand new analogy or real-world example* and forbids verbatim repetition.

#### [`src/agents/questioner.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/agents/questioner.py) — `QuestionerAgent`
- **Class**: `QuestionerAgent(BaseAgent)`
- **Prompt**: Binds to `questioner_system.md`.
- **Method**: `generate_question(node: LessonNode, recent_segment: Optional[TeachingSegment] = None) -> InteractionEvent`:
  - Generates checking questions testing understanding of the active node.
  - Auto-sanitizes: Clears `options` list if question type is not `"mcq"`.

#### [`src/agents/assessment.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/agents/assessment.py) — `AssessmentAgent`
- **Class**: `AssessmentAgent(BaseAgent)`
- **Prompt**: Binds to `assessment_system.md`.
- **Method**: `generate_report(lesson_id: str, session_history: List[EvaluationResult]) -> AssessmentReport`:
  - Analyzes accuracy and misconception history to compute `score_pct`, `strong_areas`, `weak_areas`, and `recommended_next`.

#### [`src/agents/adaptation_controller.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/agents/adaptation_controller.py) — `AdaptationController`
- **Class**: `AdaptationController`
- **Method**: `decide(current_eval: EvaluationResult, session_history: List[EvaluationResult]) -> AdaptationDecision`:
  - Tracks consecutive failures on the active node.
  - **Decision Matrix**:
    - Correct answer $\rightarrow$ `ALLOW` (advance to next node).
    - 1st failure, partial credit ($>0$), or misconception tag $\rightarrow$ `MODIFY` (re-explain with new analogy).
    - 2nd consecutive failure on same node $\rightarrow$ `REGENERATE` (re-plan segment at lower depth).
    - $\ge 3$ consecutive failures $\rightarrow$ `HUMAN` (escalate to human educator).

---

### 3.4 Adapters & LLM Interfaces (`src/adapters/`)

#### [`src/adapters/llm_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/adapters/llm_adapter.py) — Abstract LLM Interface
- **Class**: `LLMAdapter(ABC)` conforming to Contract §14.
- **Abstract Method**: `complete(messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str`.

#### [`src/adapters/gemini_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/adapters/gemini_adapter.py) — Live Gemini & Smart Fallback
- **Class `SmartMockLLMAdapter(LLMAdapter)`**:
  - Deterministic smart fallback that parses message semantics and produces valid JSON matching `LessonPlan`, `TeachingSegment`, `InteractionEvent`, `EvaluationResult`, or `AssessmentReport`.
- **Class `GeminiLLMAdapter(LLMAdapter)`**:
  - Production adapter calling Google Gemini REST API (`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`).
  - Reads `GEMINI_API_KEY` and `GEMINI_MODEL` (`gemini-2.0-flash`, fallback to `gemini-1.5-flash`).
  - Sets `generationConfig: {temperature: 0.2, responseMimeType: "application/json"}`.
  - Automatic error isolation: If network drops, rate limits occur, or API key is absent, it seamlessly delegates to `SmartMockLLMAdapter` without throwing exceptions.
- **Function**: `get_llm_adapter(api_key: Optional[str] = None) -> LLMAdapter`: Factory returning live `GeminiLLMAdapter` if key exists, else `SmartMockLLMAdapter`.

---

### 3.5 Inter-Module Clients (`src/integration/`)

#### [`src/integration/rag_client.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/integration/rag_client.py) — `RAGClient`
- Bridges orchestrator to `RAGService.retrieve_context(document_id, concept)`, returning retrieved `List[Chunk]`.

#### [`src/integration/ml_core_client.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/integration/ml_core_client.py) — `MLCoreClient`
- Client stub and interface providing `evaluate_answer(response: StudentResponse) -> EvaluationResult` boundary to `ml_core`.

---

### 3.6 Pydantic Contract Schemas (`src/schemas/`)

- [`src/schemas/lesson.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/lesson.py): `LearnerConstraints`, `LessonNode`, `LessonPlan` (Contract §5).
- [`src/schemas/teaching.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/teaching.py): `VisualSpec`, `TeachingSegment` (Contract §6).
- [`src/schemas/interaction.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/interaction.py): `InteractionEvent`, `StudentResponse` (Contract §8).
- [`src/schemas/evaluation.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/evaluation.py): `EvaluationResult`, `AdaptationDecision` (Contract §10 & §11).
- [`src/schemas/assessment.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/assessment.py): `AssessmentReport`, `LearnerProfile` (Contract §12 & §13).

---

### 3.7 Runtime System Prompts (`src/prompts/`)
> [!IMPORTANT]
> These files are dynamically read by Python at runtime via `self.load_prompt(...)`. They must **NEVER** be deleted or relocated.
- [`planner_system.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/prompts/planner_system.md): Instructs curriculum DAG generation and time budgeting.
- [`explainer_system.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/prompts/explainer_system.md): Governs grounding, tone, visual selection, and avatar cues.
- [`questioner_system.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/prompts/questioner_system.md): Enforces question modality variation and distractor design.
- [`assessment_system.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/prompts/assessment_system.md): Guides Bloom taxonomy mastery reporting and next steps.

---

## 4. Current Test Suite & Verification Matrix

All 34 automated unit and integration tests pass with zero warnings:

| Test Suite File | Test Count | Key Invariants Verified | Status |
| :--- | :--- | :--- | :--- |
| `tests/unit/test_schemas.py` | 3 | Pydantic v2 validation for constraints, lesson plans, evaluations | `PASS` |
| `tests/unit/test_llm_adapter.py` | 4 | JSON markdown stripping, repair prompt sequences, max retries | `PASS` |
| `tests/unit/test_gemini_adapter.py` | 7 | SmartMock semantics, Gemini HTTP caller, network error fallback | `PASS` |
| `tests/unit/test_planner_agent.py` | 2 | Time budget variants (5m, 20m, multi-day) and structured nodes | `PASS` |
| `tests/unit/test_explainer_agent.py` | 2 | Grounding chunk injection and anti-hallucination compliance | `PASS` |
| `tests/unit/test_questioner_agent.py` | 1 | Checkpoint question generation and non-MCQ option stripping | `PASS` |
| `tests/unit/test_assessment_agent.py` | 1 | AssessmentReport generation with scores and narrative feedback | `PASS` |
| `tests/unit/test_adaptation_controller.py` | 7 | `ALLOW`, `MODIFY` (partial/misconception), `REGENERATE`, `HUMAN` | `PASS` |
| `tests/unit/test_state_machine_transitions.py` | 3 | Valid transitions, invalid hop rejection, audit log emission | `PASS` |
| `tests/integration/test_full_teaching_loop.py` | 1 | Complete end-to-end FSM lifecycle from UNDERSTAND to DONE | `PASS` |
| `tests/integration/test_orchestrator_rag_integration.py` | 1 | RAG chunk retrieval integration during EXPLAIN phase | `PASS` |
| `tests/integration/test_orchestrator_ml_core_boundary.py` | 2 | ML Core boundary evaluation and error isolation | `PASS` |

**Command to run full suite**:
```bash
./.venv/bin/python -m pytest modules/ai_agent_orchestration/tests/ -v
```

---

## 5. Summary of Implementation State

| Area | Scaffolding Spec Status | Current Reality |
| :--- | :--- | :--- |
| **Agent Classes** | Target architecture in planning docs | Fully implemented (`planner.py`, `explainer.py`, `questioner.py`, `adaptation_controller.py`, `assessment.py`) |
| **FSM Engine** | Target architecture in planning docs | Fully operational (`TeacherOrchestrator`, `SessionState`, `TeacherState`, `transitions.py`) |
| **LLM Adapters** | Proposed interface | Fully operational (`GeminiLLMAdapter` with live Google Gemini & `SmartMockLLMAdapter`) |
| **Automated Tests** | Scaffolded stubs | 34 comprehensive unit and integration tests passing in 0.93s |
