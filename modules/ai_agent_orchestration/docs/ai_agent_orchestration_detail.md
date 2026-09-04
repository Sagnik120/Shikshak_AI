# AI Agent Orchestration Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `ai_agent_orchestration`  
> **Repository Path**: `modules/ai_agent_orchestration/`  
> **Primary Phases**: Phase 2 (Lesson Planning), Phase 3 (Explanation & Visual Selection), Phase 5 (Interaction Loop), Phase 6 (Evaluation & Adaptation), Phase 7 (Assessment)  
> **Status**: **SCAFFOLDED & CONTRACT-LOCKED** (Ready for Phase 3/5 Implementation; Highest Rubric Weight: 20 pts direct + 15 pts AI/ML)  
> **Key Contracts**: Contract §5 (`LessonPlan`), Contract §6 (`TeachingSegment`), Contract §8 (`InteractionEvent`), Contract §11 (`AdaptationDecision`), Contract §12 (`AssessmentReport`), Contract §14 (`LLMAdapter`)

---

## 1. The Task (In Simple Language)

Imagine the best human teacher you have ever had. That teacher does not simply recite a textbook from start to finish without pausing. Instead, a great teacher:
1. **Plans the curriculum**: Before entering the classroom, they structure the lesson into bite-sized steps that match the student's background and available time.
2. **Explains with vivid analogies and visuals**: They teach one concept at a time, pointing to diagrams, drawing equations, or writing code on the board.
3. **Pauses to ask checking questions**: They ask: *"Now, why does this happen?"* or *"Can you calculate the result for this case?"*
4. **Listens and detects misconceptions**: If a student gives a wrong answer, the teacher doesn't just yell "Wrong!" and move on. They diagnose *why* the student is confused (e.g. *"You confused velocity with acceleration"*).
5. **Adapts on the fly**: They explain the concept again using a fresh analogy, a simpler visual aid, or an easier example until the student understands.
6. **Produces a progress report**: At the end of the lesson, they summarize what the student mastered, what needs review, and what to study next.

The **`ai_agent_orchestration`** module is this exact pedagogical mind. It is not a single generic chatbot prompt. It is an explicit multi-agent system and state machine that acts as Planner, Explainer, Questioner, Adaptation Controller, and Assessor. It drives the entire educational journey from start to finish.

---

## 2. Technical Details & Architecture

The orchestration engine is structured as an explicit **Finite-State Machine (FSM)** and Multi-Agent Pipeline. Explicit states ensure full auditability, inspectability, and logging for the frontend right-panel audit feed.

### Multi-Agent Specialization
The module divides teaching responsibilities across 5 specialized, independently promptable LLM agents:

1. **Planner Agent**:
   - Ingests `ParsedDocument` (from RAG) or raw `topic` string, plus `LearnerConstraints` (level, language, time budget, style) and historical `LearnerProfile`.
   - Generates a structured `LessonPlan` (Contract §5) composed of ordered `LessonNode`s.
   - Respects strict time budgets:
     - **5 min**: 1–2 nodes, key concepts only, immediate summary.
     - **20 min**: 3–5 nodes, structured theory with examples and 1 checkpoint question.
     - **60 min**: 6–10 nodes, deep theory, multiple checkpoint questions, interactive exercises, and final quiz.
     - **7-day / Multi-day**: Subdivided into modular daily lesson plans.

2. **Explainer Agent**:
   - Focuses on a single `LessonNode` at a time.
   - Accepts grounded context chunks retrieved from `rag` to ensure zero hallucination.
   - Generates a `TeachingSegment` (Contract §6):
     - `script_text`: Conversational, empathetic spoken lecture text.
     - `visual_spec`: Semantic specification (`type` and `content`) for mathematical equations, Matplotlib graphs, syntax-highlighted code, or node diagrams.
     - `avatar_cue`: Directs teacher avatar facial gestures (`neutral`, `emphasis`, `questioning`).
     - Includes chunk citations (e.g., `grounded_on: ["chunk_12"]`).

3. **Questioner Agent**:
   - Activated when a `LessonNode` specifies `checkpoint_question: true`.
   - Generates an `InteractionEvent` (Contract §8).
   - Varies question modalities dynamically:
     - `mcq`: Multiple-choice with distractors designed around common misconceptions.
     - `short_answer`: Conceptual check requiring student explanation.
     - `problem`: Quantitative calculation or coding challenge.
     - `explain_in_own_words`: Metacognitive reflection prompt.

4. **Adaptation Controller**:
   - The core intelligence behind the 20-point adaptation rubric.
   - Consumes `EvaluationResult` from `ml_core` and the session's interaction history.
   - Emits an `AdaptationDecision` (Contract §11) with one of four allowed actions:
     - **`ALLOW`**: Student answered correctly with high confidence -> Advance to the next lesson node.
     - **`MODIFY`**: Student demonstrated partial understanding or an identified misconception -> Re-explain the current node with a *completely different* real-world analogy and visual aid (never repeat the old script verbatim).
     - **`REGENERATE`**: Student failed the node $\ge 2$ consecutive times -> Re-plan the node at a foundational depth level or insert a prerequisite remedial node.
     - **`HUMAN`**: Student remains blocked after regeneration -> Flag for teacher/human intervention.

5. **Assessment Agent**:
   - Evaluates the cumulative session history upon lesson completion.
   - Synthesizes an authoritative `AssessmentReport` (Contract §12):
     - Numerical score (`score_pct`).
     - Categorized list of `strong_areas` and `weak_areas`.
     - Actionable `recommended_next` study topics.
     - Personalized pedagogical narrative feedback.

---

## 3. What is Implemented Till Now (Current Status)

| Component | Implementation State | Status |
|---|---|---|
| **Contract Schemas** | Authoritative schemas defined in `instructions/Contract.md` (§5 `LessonPlan`, §6 `TeachingSegment`, §8 `InteractionEvent`, §11 `AdaptationDecision`, §12 `AssessmentReport`). | **Contract-Locked & Verified** |
| **Module Instructions** | `instructions/overview.md`, `instructions/detail_plan.md`, `instructions/contract.md` specifying exact prompt guardrails and time-budget mappings. | **Complete** |
| **Folder Architecture** | `src/` and `tests/` directories partitioned into `unit/`, `integration/`, and `e2e/`. | **Scaffolded** |
| **Planner Implementation**| Code implementation scheduled for Phase 2/3 connecting `RAGService` to LLM structured output generation. | **Next Immediate Sprint** |
| **State Machine Engine** | Finite-state machine coordinator driving `Understand -> Plan -> Explain -> Question -> Evaluate -> Adapt`. | **Next Immediate Sprint** |
| **Evaluation Harness** | E2E simulation tests in `tests/e2e/` designed to verify adaptation logic (wrong answer -> different explanation, correct answer -> advance). | **Scaffolded** |

---

## 4. Full File Structure

```
modules/ai_agent_orchestration/
├── docs/
│   └── ai_agent_orchestration_detail.md        # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Authoritative cross-module contract definitions
│   ├── detail_plan.md                          # Pedagogical multi-agent execution specifications
│   └── overview.md                             # High-level module mission statement
├── src/
│   ├── .gitkeep                                # Active source directory
│   ├── __init__.py                             # (To be created) Package exports
│   ├── agents/                                 # (Target architecture)
│   │   ├── adaptation_controller.py            # Evaluates responses and emits ALLOW / MODIFY / REGENERATE
│   │   ├── assessment_agent.py                 # Final session evaluation and AssessmentReport synthesis
│   │   ├── explainer_agent.py                  # Single-node grounded explanation and visual generator
│   │   ├── planner_agent.py                    # Multi-tier curriculum and LessonPlan generator
│   │   └── questioner_agent.py                 # Checkpoint question synthesizer (MCQ, short-answer, problem)
│   ├── models.py                               # (Target architecture) Pydantic schemas for LessonPlan, etc.
│   ├── prompts/                                # (Target architecture)
│   │   ├── adaptation_prompts.py               # Analogy-swapping and remedial prompt templates
│   │   ├── explainer_prompts.py                # Grounded explanation prompts with anti-hallucination rules
│   │   ├── planner_prompts.py                  # Curriculum structuring prompts keyed by time budget
│   │   └── questioner_prompts.py               # Question generation prompts with misconception traps
│   ├── service.py                              # (Target architecture) TeacherOrchestrationService facade
│   └── state_machine.py                        # (Target architecture) Explicit FSM state coordinator
└── tests/
    ├── e2e/
    │   └── .gitkeep                            # E2E simulated lesson session tests
    ├── integration/
    │   └── .gitkeep                            # Cross-module tests with RAG and Avatar
    └── unit/
        └── .gitkeep                            # Agent prompt & output schema validation tests
```

---

## 5. Detailed File Logic (Planned & Authoritative Architecture)

### Target Files in `src/`
- **`src/models.py`**:
  - Implements `LessonPlan` and `LessonNode` matching Contract §5:
    ```python
    class LessonNode(BaseModel):
        node_id: str
        concept: str
        depth: Literal["intro", "core", "advanced"]
        est_minutes: int
        visual_type: Literal["equation", "graph", "diagram", "code", "image", "timeline", "map", "simulation"]
        checkpoint_question: bool
    ```
  - Implements `InteractionEvent` matching Contract §8 (`node_id`, `question_text`, `type`, `options`, `expected_concept`).
  - Implements `AdaptationDecision` matching Contract §11 (`action`: `ALLOW|MODIFY|REGENERATE|HUMAN`, `target_node_id`, `reason`).
  - Implements `AssessmentReport` matching Contract §12 (`score_pct`, `strong_areas`, `weak_areas`, `recommended_next`, `narrative_feedback`).
- **`src/state_machine.py`**:
  - Coordinates the session lifecycle:
    `CREATED -> INGESTING -> PLANNED -> EXPLAINING -> AWAITING_ANSWER -> EVALUATING -> ADAPTING -> (loop) -> ASSESSING -> COMPLETE`.
  - Serializes current state, active `lesson_id`, and `node_id` into session memory so that client disconnections can be seamlessly resumed.
- **`src/agents/planner_agent.py`**:
  - Interacts with LLM via structured JSON mode.
  - Takes `LearnerConstraints` (level, language, time budget) and `DetectedStructure` from `RAGService`.
  - Distributes the available minutes across introductory, core, and advanced nodes, setting `checkpoint_question = True` on key conceptual nodes.
- **`src/agents/explainer_agent.py`**:
  - Accepts `LessonNode` and grounded text context from `RAGService.get_grounded_prompt()`.
  - Constructs `TeachingSegment`: produces empathetic, spoken narrative scripts (in the chosen language), chooses appropriate visual types, and tags avatar facial cues (`neutral`, `emphasis`, `questioning`).
- **`src/agents/questioner_agent.py`**:
  - Formulates challenging yet fair conceptual checkpoint questions. Injects plausible distractors targeting common subject misconceptions.
- **`src/agents/adaptation_controller.py`**:
  - Analyzes student performance:
    - If `EvaluationResult.correct == True`: Emits `ALLOW` to proceed.
    - If `EvaluationResult.correct == False`: Inspects `misconception_tag`. Emits `MODIFY` with specific instructions for the Explainer Agent to generate a new analogy or simpler visual aid.
    - If failure counter $\ge 2$: Emits `REGENERATE` to rebuild the sub-graph at a lower depth.
- **`src/agents/assessment_agent.py`**:
  - Summarizes total performance across all checkpoint interactions into an authoritative `AssessmentReport`.
- **`src/service.py`**:
  - Unified facade exposing `plan_lesson()`, `next_teaching_step()`, `process_student_answer()`, and `finalize_assessment()`.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Student Uploads Document or Chooses Topic]
                     |
                     v
   [Planner Agent] <---> [RAG: detected_structure]
                     |
                     v
     Generates LessonPlan (Contract §5)
  [Node 1: Intro] -> [Node 2: Core] -> [Node 3: Checkpoint]
                     |
===================== TEACHING LOOP =====================
                     |
                     v
   [Explainer Agent] <---> [RAG: retrieve_context(node)]
                     |
                     v
   TeachingSegment JSON (Contract §6)
   {node_id, script_text, visual_spec, avatar_cue}
                     |
                     v
    [avatar_voice]: Renders Video Segment
                     |
                     v
  [Frontend Center Viewport: Plays Video]
                     |
                     +---------------------------------------+
                     | Is checkpoint_question == True?       |
                     +---------------------------------------+
                        | NO                           | YES
                        v                              v
            [Advance to next node]           [Questioner Agent]
                                                       |
                                                       v
                                            InteractionEvent (Contract §8)
                                                       |
                                                       v
                                            [Frontend Interaction Card]
                                                       |
                                                       v (Student Answer)
                                            [ml_core: Evaluates Answer]
                                                       |
                                                       v
                                            EvaluationResult (Contract §10)
                                                       |
                                                       v
                                            [Adaptation Controller]
                                                       |
                    +----------------------------------+----------------------------------+
                    |                                  |                                  |
              (action=ALLOW)                    (action=MODIFY)                   (action=REGENERATE)
                    |                                  |                                  |
                    v                                  v                                  v
          [Advance to Next Node]             [Re-explain with NEW               [Lower Depth / Re-plan
                                              Analogy & Visual]                  Sub-curriculum]
                     |
===================== LESSON CONCLUSION =====================
                     |
                     v
             [Assessment Agent]
                     |
                     v
       AssessmentReport (Contract §12)
   {score_pct, strong_areas, weak_areas, recommended_next}
                     |
                     v
    [Backend: Saved to LearnerProfile]
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Inbound** | `backend` | **Contract §1, §2, §3** | Backend passes `UploadRequest` / `TopicRequest` and `LearnerConstraints` to trigger the Planner Agent. |
| **Inbound** | `rag` | **Contract §4 & Grounding** | Planner consumes `ParsedDocument.detected_structure`; Explainer consumes `GroundedContext` and chunks. |
| **Outbound** | `backend` & `frontend` | **Contract §5** (`LessonPlan`) | Returns full lesson plan structure for display on the curriculum timeline. |
| **Outbound** | `avatar_voice` | **Contract §6** (`TeachingSegment`) | Emits spoken script, visual specifications, and avatar cues to generate the video. |
| **Outbound** | `frontend` (via Backend WS) | **Contract §8** (`InteractionEvent`) | Pushes checkpoint questions to the student's interaction card. |
| **Inbound** | `ml_core` | **Contract §10** (`EvaluationResult`) | Receives student score, partial credit, and misconception tags from answer evaluation. |
| **Outbound** | `frontend` (via Backend WS) | **Contract §11** (`AdaptationDecision`) | Pushes adaptation rationale (`ALLOW`, `MODIFY`, `REGENERATE`) to the right-panel live audit log. |
| **Outbound** | `backend` | **Contract §12** (`AssessmentReport`) | Pushes final report to be stored in the permanent `LearnerProfile` (Contract §13). |
| **Internal** | `mlops` | **Contract §14** (`LLMAdapter`) | Dispatches LLM calls through the swappable adapter interface. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`ai_agent_orchestration`** module is the master conductor that controls:
- **Plan**: Coordinates the Planner Agent.
- **Explain & Demonstrate**: Directs the Explainer Agent and triggers `avatar_voice`.
- **Question**: Triggers the Questioner Agent.
- **Adapt & Continue**: Triggers the Adaptation Controller based on `ml_core` evaluations, determining whether to continue (`ALLOW`), remediate (`MODIFY`), or restart (`REGENERATE`).

---

## 9. Critical Notes for Any LLM Agent Working on This Module

> [!IMPORTANT]
> **Strict Guardrails for LLM Agents:**
> 1. **No Single-Prompt Shortcuts**: The evaluation rubric explicitly awards 20 points for "genuine AI-driven teaching capability and adaptation". Never collapse this module into a single giant LLM prompt. Every agent stage must be an explicit, modular call emitting structured JSON.
> 2. **Strict JSON Mode**: Every agent prompt must mandate JSON output matching the authoritative schemas in `instructions/Contract.md`. Never allow free-text markdown responses between internal agents.
> 3. **Never Repeat Verbatim on `MODIFY`**: If `AdaptationDecision.action == "MODIFY"`, the Explainer Agent prompt must explicitly forbid repeating the previous explanation. It must supply an alternative real-world analogy, a different visual format, or a simpler step-by-step breakdown.
> 4. **Hallucination Containment**: When teaching from an uploaded document, the Explainer Agent must strictly adhere to the retrieved context chunks. If a concept is outside the chunks, it must explicitly preface the sentence with *"Based on general knowledge..."*
> 5. **Audit Logging**: Every transition in the state machine and every `AdaptationDecision` must be logged and forwarded to the backend WebSocket so the student and evaluators can view the live reasoning feed in the UI right-panel.
