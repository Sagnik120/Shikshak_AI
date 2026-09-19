# AI Agent Orchestration — Live Gemini Web Test Guide

## 1. Purpose
This document provides the definitive manual test specification for the `ai_agent_orchestration` module. It defines exactly how a human QA engineer can independently verify the core teaching logic, state transitions, and live Gemini interactions using the isolated web testbed, without needing the full system stack (Frontend/Backend/RAG/ML Core) to be completely wired up.

## 2. Scope
This test guide focuses strictly on the pedagogical FSM and agent generations:
- `PlannerAgent`
- `ExplainerAgent`
- `QuestionerAgent`
- `AdaptationController`
- `AssessmentAgent`
- `TeacherOrchestrator`

It covers both **LIVE GEMINI** executions and the deterministic state transitions.

## 3. Current Web Test Architecture
The testbed (`modules/ai_agent_orchestration/tests/web_test/server.py`) runs on **Port 8001**.
It imports the real production components but mocks external integrations using `IsolatedRAGClientStub`, `IsolatedMLCoreClientStub`, and `IsolatedAvatarClientStub`. This ensures that any failures observed here are strictly the fault of the orchestration module or the Gemini generation, not the downstream modules.

## 4. How LIVE Gemini Mode Works
When the "Use Live LLM" toggle is active (or `use_live_llm=True` in the API payload):
1. The testbed requests the `GeminiLLMAdapter` from the adapter factory with `raise_on_failure=True`.
2. The adapter reads `GEMINI_API_KEY` from the environment.
3. It makes a real network request to the Google Gemini API.
4. If the request succeeds, the live generation is returned.
5. If the request fails (e.g., bad key, network issue), an **explicit runtime error is raised** and displayed in the UI, preventing false positives.

## 5. How SmartMock Mode Works
When the "Use Live LLM" toggle is inactive:
1. The testbed uses the `SmartMockLLMAdapter`.
2. This adapter does **not** make any network calls.
3. It performs basic intent matching on the system prompt and returns hardcoded, deterministically correct JSON payloads matching the `Contract.md` schemas.
4. This mode is used for rapid verification of the state machine transitions without burning API quota or dealing with non-deterministic text.

## 6. How to Start the Testbed
1. Open a terminal at the repository root.
2. Activate your virtual environment: `.\venv\Scripts\Activate.ps1`
3. Run the testbed server:
   ```bash
   python -m modules.ai_agent_orchestration.tests.web_test.server
   ```
4. Open a browser to: `http://localhost:8001`

## 7. How to Verify Which LLM Mode Is Active
Check the "Testbed Status" indicator at the top of the UI.
Additionally, when you perform an operation in **LIVE GEMINI** mode, if the API key is missing or invalid, you will see a bold 500 error: `LIVE GEMINI failure: ...` instead of a successful response. 

## 8. Gemini API Safety Notes
- The human tester owns the API key.
- **The key must remain in the `.env` file at the repository root.**
- NEVER paste the key directly into the UI fields.
- NEVER expose the key in logs or commit it to version control.
- Live Gemini verification must be performed manually by the human tester.

## 9. Test Environment / Prerequisites
- `.env` file present at the repo root containing a valid `GEMINI_API_KEY`.
- Python 3.12+ with all dependencies in `requirements.txt` installed.

## 10. Planner Test Matrix
Execute these cases in the Planner section of the testbed using **LIVE GEMINI**.

| Test ID | Purpose | Input Values | Expected Output Properties | Priority |
|---|---|---|---|---|
| **P-01** | Basic topic planning | Topic: "Newton's Laws of Motion", Level: Beginner, Time: 15m | Valid `LessonPlan` schema; contains ordered nodes; appropriate beginner depth; time budget respected. | P0 |
| **P-02** | Short time budget | Topic: "Newton's Laws of Motion", Level: Beginner, Time: 5m | Significantly smaller lesson plan; prioritizes core concept; avoids deep tangents. | P0 |
| **P-03** | Medium time budget | Time: 20m | More structured coverage; includes examples and checkpoints. | P0 |
| **P-04** | Long time budget | Time: 60m | Deeper progression; multiple checkpoints. | P1 |
| **P-05** | Different learner level | Level: Advanced | Content depth and terminology adapt to an advanced audience. | P1 |
| **P-06** | Different teaching styles | Style: "Socratic" | Output reflects the selected style in the node descriptions without violating schema. | P1 |
| **P-07** | Different language | Language: Hindi / "hi" | Generated lesson concepts follow the selected language; schema remains valid. | P1 |
| **P-08** | Source-grounded | Document text provided | Plan stays relevant to supplied material instead of general knowledge. | P1 |
| **P-10** | Edge input | Topic: "xyz!!!", very short | No server crash; returns a valid schema or a clear validation error. | P1 |

## 11. Explainer Test Matrix
Execute these cases in the Explainer section using **LIVE GEMINI**.

| Test ID | Purpose | Input Values | Expected Output Properties | Priority |
|---|---|---|---|---|
| **E-01** | Basic explanation | Concept: "Newton's First Law" | Valid `TeachingSegment`; coherent script; visual specification matches type; appropriate learner level. | P0 |
| **E-02** | Visual types | Cycle through diagram, equation, graph, code | Schema valid; semantic suitability of the visual spec content. | P1 |
| **E-03** | Grounded explanation | Provide specific grounding chunks | Explanation explicitly uses supplied evidence and does not invent facts. | P0 |
| **E-04** | Empty grounding | No grounding chunks | Behavior matches contract; fallback to general knowledge without crashing. | P1 |
| **E-05** | MODIFY explanation | Feedback: "Student confused velocity with force" | Explanation specifically addresses the misconception using a NEW analogy, avoiding repetition. | P0 |
| **E-06** | Learner levels | Levels: Beginner vs Advanced | Terminology complexity adapts accordingly. | P1 |
| **E-08** | Edge concept input | Invalid/gibberish concept | Controlled validation error; no malformed response JSON. | P1 |

## 12. Questioner Test Matrix
Execute these cases in the Questioner section using **LIVE GEMINI**.

| Test ID | Purpose | Input Values | Expected Output Properties | Priority |
|---|---|---|---|---|
| **Q-01** | MCQ Modality | Concept: "Inertia" | Valid `InteractionEvent`; type is 'mcq'; distractor options are coherent; expected concept clearly answerable. | P0 |
| **Q-02** | Short Answer | Concept: "Force" | Type is 'short_answer'; NO options provided; clear question. | P0 |
| **Q-03** | Problem Solving | Concept: "F=ma calculation" | Clear numerical or applied problem. | P1 |
| **Q-04** | Misconception-oriented | Based on previous failure | Question specifically targets distinguishing the previously failed concept. | P1 |

## 13. Adaptation Controller Test Matrix
*Note: This component is deterministic. LIVE GEMINI is not strictly required.*

| Test ID | Purpose | Input Values | Expected Decision | Priority |
|---|---|---|---|---|
| **A-01** | Correct answer | correct: True, partial: 0.0 | **ALLOW** | P0 |
| **A-02** | Partial answer | correct: False, partial: 0.5 | **MODIFY** | P0 |
| **A-03** | First incorrect w/ misconception | correct: False, consecutive_failures: 1, misconception: "confused_f_v" | **MODIFY** | P0 |
| **A-04** | Second consecutive failure | correct: False, consecutive_failures: 2 | **REGENERATE** | P0 |
| **A-05** | Third consecutive failure | correct: False, consecutive_failures: 3 | **HUMAN** | P0 |
| **A-08** | Different misconception tags | correct: False, partial: 0.0, various tags | **MODIFY** | P1 |

## 14. FSM Test Matrix

### How to use the FSM Step Simulator
The FSM Step Simulator executes **one state transition at a time**. Because the session is stored in memory, **if you restart the server, your session is erased** and you must start from `UNDERSTAND` again.

**Crucial Rules for FSM Testing:**
1. **Always start from `UNDERSTAND`**: If you jump straight to `PLAN` or `EXPLAIN` without running the previous steps, the server will error out because the session is missing required context (like constraints or the lesson plan).
2. **Inputs JSON Payload**: This field is ONLY for providing external data required by the specific state you are running. 
   - **DO NOT** paste the output of the previous step here. 
   - If the state doesn't require input, leave it as `{}`.

**Expected Inputs per State:**
* `UNDERSTAND`: Requires constraints. 
  `{"constraints": {"level": "beginner", "language": "en", "time_budget_min": 15}}`
* `PLAN`, `EXPLAIN`, `DEMONSTRATE`, `QUESTION`, `CONTINUE`: Leave input as `{}` (They pull data directly from the in-memory session).
* `EVALUATE`: Requires a simulated student answer.
  `{"student_response": "I think inertia means an object wants to stop."}`
* `ADAPT`: Leave input as `{}` to use the actual student evaluation from the previous step. **OR**, you can force a specific adaptation decision by injecting a mock evaluation result:
  - Force **ALLOW** (Continue): `{"eval_result": {"node_id": "test", "correct": true, "partial_credit": 1.0, "confidence": 1.0, "feedback_text": "Perfect."}}`
  - Force **MODIFY** (Remediation): `{"eval_result": {"node_id": "test", "correct": false, "partial_credit": 0.0, "confidence": 1.0, "feedback_text": "Failed.", "misconception_tag": "confused_concept"}}`
  - *(Note: ADAPT is deterministic, meaning it uses rules rather than LLM generation to decide what to do next based on the evaluation).*

Execute the following flow in order using **SMART MOCK** to quickly test flow logic.

| Test ID | Transition Tested | Expected Result | Priority |
|---|---|---|---|
| **F-01** | UNDERSTAND → PLAN | State updates to PLAN; Plan artifact stored in session. | P0 |
| **F-02** | PLAN → EXPLAIN | State updates to EXPLAIN; segment artifact created. | P0 |
| **F-03** | EXPLAIN → DEMONSTRATE | State updates to DEMONSTRATE. | P0 |
| **F-04** | DEMONSTRATE → QUESTION | State updates to QUESTION if checkpoint enabled. | P0 |
| **F-05** | QUESTION → EVALUATE | State updates to EVALUATE upon student answer. | P0 |
| **F-06** | EVALUATE → ADAPT | State updates to ADAPT. | P0 |
| **F-07** | ADAPT → CONTINUE | If ALLOW, updates to CONTINUE, then moves to next node (EXPLAIN). | P0 |
| **F-08** | ADAPT → EXPLAIN | If MODIFY, loops back to EXPLAIN for the same node. | P0 |
| **F-09** | ADAPT → PLAN | If REGENERATE, loops back to PLAN for the segment. | P0 |
| **F-10** | ADAPT → HUMAN_ESCALATION | If HUMAN, halts in HUMAN_ESCALATION state. | P0 |
| **F-11** | CONTINUE → DONE | If last node completed, state updates to DONE. | P0 |
| **F-12** | Invalid Transition | Send DEMONSTRATE → ADAPT | Rejected; error returned; state unchanged. | P1 |

## 15. Assessment Test Matrix
Execute in the Assessment section using **LIVE GEMINI**.

| Test ID | Purpose | Input Values | Expected Output Properties | Priority |
|---|---|---|---|---|
| **AS-01** | Perfect history | Session history full of ALLOW decisions | High score; strong areas populated; appropriate next-study recommendation. | P0 |
| **AS-02** | Mixed performance | Mixed ALLOW and MODIFY decisions | Score reflects history; weak areas identify the exact problematic concepts. | P0 |
| **AS-03** | Repeated misconception | Multiple REGENERATE/HUMAN decisions | Misconception history heavily influences weak-area reporting. | P1 |
| **AS-04** | Empty history | Empty session log | Controlled behavior; schema-valid response indicating lack of data. | P1 |

## 16. Full Teaching Loop Scenarios
Execute in the FSM Step Simulator. Ensure **LIVE GEMINI** is turned ON for the LLM steps.

### FULL-01 Successful learner
1. **UNDERSTAND → PLAN → EXPLAIN → DEMONSTRATE → QUESTION** (All Gemini generation steps).
2. Input correct answer.
3. **EVALUATE → ADAPT** (ALLOW decision).
4. **CONTINUE → EXPLAIN** (Next node).
**Verify:** Every generation uses live Gemini successfully without crashes, JSON formats are preserved, and state advances correctly.

### FULL-02 First-attempt misconception
1. **PLAN → EXPLAIN → DEMONSTRATE → QUESTION**
2. Input incorrect answer.
3. **EVALUATE → ADAPT** (MODIFY decision).
4. **EXPLAIN** again.
**Verify (HUMAN JUDGEMENT REQUIRED):** The second explanation generated by Gemini must be meaningfully different and address the identified misconception. It must NOT simply repeat the first explanation.

### FULL-03 Repeated failure
1. First failure → **MODIFY**
2. Second failure → **REGENERATE**
3. Third failure → **HUMAN_ESCALATION**
**Verify:** Exact transition behavior is enforced by the Controller.

## 17. Error / Edge Cases
- **Missing API Key**: Ensure that clicking "Run" with LIVE GEMINI active and no API key in `.env` causes a loud error in the UI.
- **Malformed Input**: Submit empty topics or missing fields. The backend should reject them with a 422 Validation Error gracefully.

## 18. Expected Output Rules
When evaluating the LLM outputs during these tests, use these three levels:
* **REQUIRED**: Must always hold. Valid Pydantic schema, no malformed JSON, all required fields present, valid enum values.
* **EXPECTED**: Normally should hold. Relevant content, appropriate depth, correct language.
* **HUMAN JUDGEMENT**: Requires manual inspection. Explanation feels pedagogically useful, analogies are genuinely different on MODIFY, questions are meaningful.

## 19. Pass/Fail Recording Template
When conducting this manual QA, record results in the following format:
```text
Date: [YYYY-MM-DD]
Tester: [Name]
Model: [Gemini Version]

| Test ID | Pass/Fail | Notes |
|---------|-----------|-------|
| P-01    |           |       |
...
```

## 20. Recommended Manual Test Order
1. Setup `.env` and start the server (`Port 8001`).
2. Run **F-01 to F-11** (FSM Matrix) using **SMART MOCK** to ensure basic transition sanity.
3. Turn ON **LIVE GEMINI** and intentionally remove the `GEMINI_API_KEY` from `.env`. Run a Planner test to verify explicit failure (Error Handling). Replace the key.
4. Run **P-01** (Planner) and **E-01** (Explainer) on LIVE GEMINI to ensure the network path works.
5. Execute **FULL-02** to test the pedagogical adaptation loop.

## 21. Known Limitations
- The current web UI relies on manual step triggers for the FSM; it does not automatically advance like the production WebSocket system will.
- ML Core evaluations are simulated using the mock client in this testbed to isolate the Orchestrator's behavior.

## 22. What This Test Does NOT Prove
Passing this isolated orchestration test does **NOT** automatically prove:
- RAG production integration
- ML Core production integration
- Avatar/Voice production integration
- Backend REST integration
- Frontend UI rendering
- WebSocket end-to-end event streaming

**It proves ONLY** that the orchestration module itself behaves correctly under the tested conditions, its internal FSM is sound, and its LLM-backed operations generate valid schema-compliant JSON using the intended live Gemini adapter path.
