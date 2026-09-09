# overview.md — ai_agent_orchestration

## 1. What This Module Does
The **`ai_agent_orchestration`** module is the pedagogical core of Shikshak AI. It functions as an autonomous, multi-agent pedagogical pipeline and finite-state machine (FSM) that models the cognitive workflow of an expert human teacher:
1. **Curriculum Planning (`PlannerAgent`)**: Transforms uploaded material or raw topic strings into structured `LessonPlan` DAGs adapted to learner level, language, and time budgets (5m, 15m, 30m, 60m, multi-day).
2. **Concept Explanation (`ExplainerAgent`)**: Synthesizes grounded spoken lecture scripts, selects appropriate visual formats (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`), and tags teacher avatar cues (`neutral`, `emphasis`, `questioning`).
3. **Formative Questioning (`QuestionerAgent`)**: Generates contextual checkpoint questions across multiple modalities (`mcq`, `short_answer`, `problem`, `application`, `explain_in_own_words`).
4. **Pedagogical Adaptation (`AdaptationController`)**: Evaluates student answer scores, confidence, and misconception tags from `ml_core` to make real-time decisions: `ALLOW` (advance), `MODIFY` (re-explain with brand new analogy), `REGENERATE` (re-plan segment at lower depth), or `HUMAN` (escalate to instructor).
5. **Comprehensive Assessment (`AssessmentAgent`)**: Evaluates cumulative session history to synthesize an authoritative `AssessmentReport` with Bloom taxonomy mastery analysis and next-step recommendations.
6. **Orchestration & State Machine (`TeacherOrchestrator`)**: Drives the 10-state session lifecycle (`UNDERSTAND -> PLAN -> EXPLAIN -> DEMONSTRATE -> QUESTION -> EVALUATE -> ADAPT -> CONTINUE -> DONE -> HUMAN_ESCALATION`).
7. **Isolated Interactive Testing (`tests/web_test/`)**: Dedicated web testbed on port 8001 with fine-grained structured execution logging (`tests/web_test/logs/`).

---

## 2. Essential Reading Before Modifying This Module
1. [`instructions/Contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md) (Root schema definitions §5, §6, §8, §10, §11, §12, §14)
2. [`docs/spec/06_Memory.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/06_Memory.md) (L2 fast-context cache and active operational focus)
3. [`docs/spec/02_Architecture.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/02_Architecture.md) (System-wide subsystem boundaries)
4. [`modules/ai_agent_orchestration/docs/ai_agent_orchestration_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/docs/ai_agent_orchestration_detail.md) (Complete code-level file guide)
5. [`modules/ai_agent_orchestration/instructions/detail_plan.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/instructions/detail_plan.md) (Agent requirements and testbed plan)
6. [`modules/ai_agent_orchestration/instructions/contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/instructions/contract.md) (Module-internal types and contract bindings)

---

## 3. Key Invariants & Safety Rules
- **Runtime Prompt Protection**: Files in `src/prompts/*.md` are dynamically read by Python code (`self.load_prompt(...)`). **NEVER move, rename, or delete them.**
- **Backend Isolation**: Testing code in `tests/web_test/` runs on dedicated port 8001. Never modify `modules/backend/src/` to inject test-only endpoints.
- **Single Source of Truth**: All testing harnesses directly import from `modules.ai_agent_orchestration.src.*`. Any bug fixes applied to `src/` automatically benefit the full application.
