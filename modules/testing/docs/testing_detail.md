# Testing Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `testing`  
> **Repository Path**: `modules/testing/` (and root `tests/`, `scripts/run_all_diagnostics.py`)  
> **Primary Role**: Cross-Module End-to-End Test Harness, Pedagogical Adaptation Verifier & Regression Suite  
> **Status**: **ACTIVE & EXTENSIBLE** (Root test suite fully operational with 35+ automated tests passing)  
> **Key Coverage**: End-to-End Teaching Simulations, RAG Groundedness Evals, Multilingual Invariants QA & Video Visual Verification

---

## 1. The Task (In Simple Language)

Imagine an educational quality inspector and mock student rolled into one:
1. **The Mock Student**: Simulates realistic student behaviors:
   - A brilliant student who gets every question right on the first try.
   - A confused student who makes common mistakes (e.g. confusing velocity with acceleration).
   - A completely lost student who fails repeatedly.
2. **Checking the Teacher's Response**:
   - When the student gets it right, did the teacher praise them and move to the next topic?
   - When the student made a mistake, did the teacher provide a *new*, different analogy? (If the teacher just repeats the same exact words, the inspector fails the test!).
   - If the student fails repeatedly, does the teacher lower the difficulty or ask for human help?
3. **Checking Document Grounding**: Did the teacher stick to the facts in the uploaded textbook, or did they hallucinate fake facts?
4. **Checking Multilingual Consistency**: Does the lesson structure stay identical when taught in English versus Hindi, while speaking the correct language fluently?

The **`testing`** module is this educational inspector for Shikshak AI. It provides an automated suite of end-to-end simulators, groundedness evaluators, visual asset inspectors, and regression runners that prove the system actually works and behaves like a human teacher.

---

## 2. Technical Details & Architecture

The testing harness is organized into 5 specialized validation tiers:

### 1. E2E Pedagogical Adaptation Simulator (`tests/e2e/`)
Simulates scripted multi-turn student sessions against the full state machine:
- **Assertion 1 (Adaptation Novelty)**: Asserts that when an answer is incorrect, the generated `TeachingSegment.script_text` is semantically distinct from the initial explanation (Levenshtein distance & semantic divergence check).
- **Assertion 2 (Progression)**: Asserts that a correct answer advances `active_node_id` forward in the lesson graph.
- **Assertion 3 (Escalation)**: Asserts that $\ge 2$ consecutive failures on the same node trigger `AdaptationDecision.action == "REGENERATE"`, and further failure escalates to `"HUMAN"`.
- **Assertion 4 (Assessment Sanity)**: Asserts that the final `AssessmentReport.score_pct` is strictly within $[0, 100]$ and that `weak_areas` reflect the concepts the student struggled with.

### 2. RAG Groundedness & Anti-Hallucination Evaluator (`tests/eval/`)
- Ingests standard benchmark documents (`tests/fixtures/sample_physics.pdf`).
- Queries concepts and asserts that retrieved candidate chunks match expected chunk IDs.
- Verifies that generated explanation scripts do not introduce facts absent from the top-k retrieved chunks.

### 3. Multilingual Invariants QA (`tests/eval/`)
- Requests the identical curriculum topic under `language="en"` and `language="hi"`.
- Asserts structural invariance: `LessonPlan` node count, concept order, and depth levels are identical.
- Asserts linguistic fidelity: `script_text` and TTS audio generate correctly in their respective target languages without crashing or resetting progress.

### 4. Visual Asset Type Verifier (`tests/integration/`)
- Asserts that when a lesson node specifies `visual_type="equation"`, the generated visual artifact is a rendered LaTeX image, not a generic fallback.
- Asserts that `visual_type="code"` renders dark-themed code slides with line numbers.

### 5. Unified Diagnostic Runner (`scripts/run_all_diagnostics.py`)
- Single-command CLI script that executes all unit, integration, smoke, and eval suites, generating a timestamped pass/fail report automatically recorded in `docs/progress.md`.

---

## 3. What is Implemented Till Now (Current Status)

| Test Suite | Location | Status |
|---|---|---|
| **Root Regression Runner** | `scripts/run_all_diagnostics.py` / `pytest.ini` running all tests across the repository. | **Operational & Verified** |
| **RAG Pipeline Tests** | `tests/integration/test_rag_pipeline_deep.py`, `tests/smoke/test_rag_smoke.py`, `tests/unit/test_rag_parsers_deep.py`, `tests/eval/test_rag_eval_rubric.py`. | **35/35 Tests Passing** |
| **Avatar & Voice Tests** | `tests/integration/test_avatar_voice_pipeline_deep.py`, `tests/smoke/test_avatar_voice_smoke.py`, `tests/unit/test_avatar_voice_deep.py`, `tests/eval/test_avatar_voice_eval.py`. | **All Passing** |
| **Module Unit Tests** | `modules/avatar_voice/tests/` (10 test files) and `modules/rag/tests/` (parsers, models, chunkers). | **All Passing** |
| **Simulated E2E State Machine**| `tests/e2e/` test scaffolding ready for `ai_agent_orchestration` Phase 5 integration. | **Scaffolded** |

---

## 4. Full File Structure

```
modules/testing/
├── docs/
│   └── testing_detail.md                       # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Authoritative cross-module contract definitions
│   ├── detail_plan.md                          # Testing harness specifications and rubric assertions
│   └── overview.md                             # High-level module summary
├── src/
│   ├── .gitkeep                                # Active source directory
│   ├── __init__.py                             # (Target architecture) Package exports
│   ├── fixtures_loader.py                      # Utilities for loading sample documents and scripts
│   ├── mocks/                                  # (Target architecture)
│   │   ├── mock_llm.py                         # Deterministic mock LLM adapter returning fixture JSON
│   │   └── mock_student.py                     # Scripted student response generators (Good/Bad/Confused)
│   ├── runners/                                # (Target architecture)
│   │   └── diagnostic_runner.py                # Diagnostics execution and markdown report generator
│   └── validators/                             # (Target architecture)
│       ├── adaptation_validator.py             # Asserts re-explanation divergence and state escalation
│       └── groundedness_validator.py           # Asserts citation accuracy and hallucination bounds
└── tests/
    ├── e2e/
    │   └── .gitkeep                            # Module-level E2E tests
    ├── integration/
    │   └── .gitkeep                            # Module-level integration tests
    └── unit/
        └── .gitkeep                            # Module-level unit tests
```

---

## 5. Detailed File Logic (Planned & Authoritative Architecture)

### Target Files in `src/`
- **`src/mocks/mock_student.py`**:
  - `ScriptedStudent`: Configurable test actor simulating three student archetypes:
    - `MasteryStudent`: Always returns the correct answer with short response times.
    - `MisconceptionStudent`: Always selects distractors tagged with specific physics/math misconceptions.
    - `StrugglingStudent`: Submits wrong answers repeatedly to test escalation to `REGENERATE` and `HUMAN`.
- **`src/mocks/mock_llm.py`**:
  - Offline `LLMAdapter` returning pre-recorded, contract-compliant JSON fixtures for deterministic CI testing without incurring API costs.
- **`src/validators/adaptation_validator.py`**:
  - Implements `validate_adaptation_sequence()`:
    - Compares original script $S_1$ and modified script $S_2$ using SequenceMatcher and token overlap. Fails if similarity exceeds 80%.
    - Validates that state transitions follow Contract §11 rules.
- **`src/validators/groundedness_validator.py`**:
  - Implements `validate_grounding()`:
    - Verifies that all facts cited in the teaching segment exist within the retrieved text chunks.
- **`src/fixtures_loader.py`**:
  - Provides helper methods `load_fixture_pdf()`, `load_fixture_docx()`, and `load_canned_responses()`.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Developer / CI Runner triggers: python scripts/run_all_diagnostics.py]
                                 |
                                 v
         +-----------------------+-----------------------+
         |                                               |
[Tier 1: Unit & Smoke Tests]                   [Tier 2: E2E Simulation]
Runs fast schema, parser & audio tests         Mounts ScriptedStudent (Mock)
(Executes in < 5 seconds)                                |
         |                                               v
         |                                  Drives Teaching Loop:
         |                                  Node 1 -> Question 1 -> Wrong Answer
         |                                               |
         |                                               v
         |                                  [adaptation_validator.py]
         |                                  Asserts:
         |                                  - Script is DIFFERENT
         |                                  - AdaptationDecision == MODIFY
         |                                  - Misconception addressed
         |                                               |
         +-----------------------+-----------------------+
                                 |
                                 v
                     [Tier 3: Groundedness Eval]
                     Asserts:
                     - Explanations bound to chunks
                     - Citation IDs correctly tagged
                                 |
                                 v
                     [Tier 4: Multilingual QA]
                     Asserts:
                     - English and Hindi lesson plans match
                     - Mid-lesson language switch maintains node_id
                                 |
                                 v
                 [Generates Diagnostics Report]
                 Updates docs/progress.md with pass/fail summary
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Drives** | `ai_agent_orchestration` | **Contracts §5, §6, §8, §11, §12** | Simulates full state machine sessions and asserts valid contract transitions. |
| **Evaluates** | `rag` | **Contract §4** | Verifies parsing accuracy and chunk retrieval relevance. |
| **Evaluates** | `avatar_voice` | **Contracts §6, §7** | Validates that rendered video durations and visual types match specifications. |
| **Evaluates** | `ml_core` | **Contracts §9, §10** | Tests MCQ accuracy, semantic evaluation scoring, and misconception classifications. |
| **Simulates** | `backend` & `frontend` | **Contracts §1, §2, §8, §9** | Emulates REST uploads and WebSocket frames. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`testing`** module acts as the automated benchmark and auditor for all 8 stages:
- Verifies **Understand** (RAG parsing).
- Verifies **Plan** (Curriculum structuring).
- Verifies **Explain & Demonstrate** (Video synthesis & visual types).
- Verifies **Question & Evaluate** (Answer scoring & misconception tagging).
- Verifies **Adapt & Continue** (Adaptive re-explanation and state machine escalation).

---

## 9. Critical Notes for Any LLM Agent Working on This Module

> [!IMPORTANT]
> **Strict Guardrails for LLM Agents:**
> 1. **Zero External Network Calls in CI**: All unit and smoke tests must execute locally without requiring internet access or paid API keys. Always use `mock_llm.py`, `FallbackTTSAdapter`, and local test fixtures.
> 2. **Divergence Assertion Sensitivity**: In adaptation tests, never assert exact string inequality (`assert s1 != s2`). Two explanations could differ by a single comma and still be repetitive. Always assert semantic divergence or token overlap $< 80\%$.
> 3. **Non-Destructive Test Cleanups**: Any temporary video files, audio clips, or test vector collections generated during test runs must be cleaned up in a `finally` block or pytest fixture teardown.
> 4. **Keep Diagnostics Fast**: Smoke and unit tests must execute in under 15 seconds so developers and automated agents can run them frequently during active coding.
