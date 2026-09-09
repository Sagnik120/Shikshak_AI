# contract.md — ai_agent_orchestration (Module Contract & Internal Types)

This module implements and consumes the canonical schemas defined in the root [`instructions/Contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md).

---

## 1. Cross-Module Contract Mappings

| Contract Section | Schema Name | Schema File | Implementation Role |
| :--- | :--- | :--- | :--- |
| **Contract §5** | `LessonPlan`, `LessonNode`, `LearnerConstraints` | [`src/schemas/lesson.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/lesson.py) | Produced by `PlannerAgent.plan_lesson()`; defines structured curriculum DAG. |
| **Contract §6** | `TeachingSegment`, `VisualSpec` | [`src/schemas/teaching.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/teaching.py) | Produced by `ExplainerAgent.generate_segment()`; consumed by `avatar_voice` for video synthesis. |
| **Contract §8** | `InteractionEvent`, `StudentResponse` | [`src/schemas/interaction.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/interaction.py) | Produced by `QuestionerAgent.generate_question()`; sent to frontend interaction cards. |
| **Contract §10 & §11** | `EvaluationResult`, `AdaptationDecision` | [`src/schemas/evaluation.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/evaluation.py) | Ingests `EvaluationResult` from `ml_core`; `AdaptationController` emits `AdaptationDecision` (`ALLOW`, `MODIFY`, `REGENERATE`, `HUMAN`). |
| **Contract §12 & §13** | `AssessmentReport`, `LearnerProfile` | [`src/schemas/assessment.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/schemas/assessment.py) | Produced by `AssessmentAgent.generate_report()`; stored in persistent learner profile. |
| **Contract §14** | `LLMAdapter` | [`src/adapters/llm_adapter.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/adapters/llm_adapter.py) | Abstract completion interface implemented by `GeminiLLMAdapter` and `SmartMockLLMAdapter`. |

---

## 2. Module-Internal Types (Not Part of Cross-Module Contract)

These types are private to `ai_agent_orchestration` and are used for FSM state management, session tracking, and testing:

### 2.1 State Machine Internal Types
- **`TeacherState`** ([`src/state_machine/states.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/state_machine/states.py)):  
  `Enum` defining the 10 states of the pedagogical cycle:
  `UNDERSTAND`, `PLAN`, `EXPLAIN`, `DEMONSTRATE`, `QUESTION`, `EVALUATE`, `ADAPT`, `CONTINUE`, `DONE`, `HUMAN_ESCALATION`.
- **`SessionState`** ([`src/state_machine/session_state.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/state_machine/session_state.py)):  
  `dataclass` maintaining active session runtime memory:
  - `session_id: str`
  - `lesson_plan: Optional[LessonPlan]`
  - `current_node_index: int`
  - `evaluation_history: List[EvaluationResult]`
  - `state_logs: List[dict]`
  - `constraints: Optional[LearnerConstraints]`
  - `topic: Optional[str]`, `document_id: Optional[str]`
  - `current_feedback_override: Optional[str]` (Remedial prompt injected on `MODIFY`)
  - `recent_segment: Optional[TeachingSegment]`, `recent_question: Optional[InteractionEvent]`
- **`VALID_TRANSITIONS`** ([`src/state_machine/transitions.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/src/state_machine/transitions.py)):  
  Dictionary mapping each `TeacherState` to allowed target states in the directed graph.

### 2.2 Testbed & Logging Types
- **`ExecutionTrace`** ([`tests/web_test/logger.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/tests/web_test/logger.py)):  
  Trace container tracking checkpoints (`timestamp`, `file`, `function`, `step`), raw LLM prompts, completions, and error tracebacks.
- **Testbed Request Schemas** ([`tests/web_test/server.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/tests/web_test/server.py)):  
  `PlannerTestRequest`, `ExplainerTestRequest`, `QuestionerTestRequest`, `AdaptationTestRequest`, `AssessmentTestRequest`, `FSMStepRequest`.
