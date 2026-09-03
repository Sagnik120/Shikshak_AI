# ML Core Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `ml_core`  
> **Repository Path**: `modules/ml_core/`  
> **Primary Role**: Student Response Evaluation, Misconception Taxonomy Classification, Key-Term Extraction & Visual Type Heuristics  
> **Status**: **SCAFFOLDED & CONTRACT-LOCKED** (Ready for answer evaluation & misconception classifier implementation)  
> **Key Contracts**: Contract §9 (`StudentResponse`), Contract §10 (`EvaluationResult`), Contract §5 (`LessonPlan.visual_type`), Contract §6 (`TeachingSegment.visual_spec`)

---

## 1. The Task (In Simple Language)

Imagine a teaching assistant grading a student's quiz:
1. **Grading Multiple Choice**: Checks the answer against the answer key instantly without second-guessing.
2. **Grading Written Explanations**: When a student writes an explanation in their own words, the assistant doesn't just look for exact keyword matches. They read for conceptual understanding, giving partial credit if the core logic is half-correct.
3. **Diagnosing Misconceptions**: If a physics student writes *"A heavy stone falls faster than a light pebble because gravity pulls it harder,"* the assistant recognizes the classic misconception: *"Confuses gravitational force with gravitational acceleration."* The assistant tags this exact misconception so the teacher knows *why* the student is mistaken.
4. **Picking the Best Teaching Visual**: When the teacher prepares a slide on quadratic equations, the assistant says: *"Use a coordinate graph and a LaTeX formula, not a flowchart."* When teaching photosynthesis, they say: *"Use a labeled cycle diagram."*

The **`ml_core`** module is this exact grading assistant and pedagogical classifier. It provides lightweight, high-speed machine learning models and deterministic heuristics that are cheaper, faster, and more reliable than making costly, slow LLM calls for every single evaluation.

---

## 2. Technical Details & Architecture

The module is engineered to balance deterministic accuracy, low inference latency, and cognitive flexibility:

### Hybrid Answer Evaluation Engine
Student responses are evaluated through a two-stage hybrid pipeline:
- **Tier 1 (Deterministic Rule Match for MCQs)**:
  - For multiple-choice questions, compares `StudentResponse.raw_answer` directly with `expected_concept` or answer keys.
  - Zero latency, zero cost, and 100% deterministic accuracy (zero hallucination risk).
- **Tier 2 (Embedding Cosine Similarity + Constrained LLM Judge for Free-Text)**:
  - For short-answer and conceptual questions, first runs cosine similarity between the student's answer embedding and the reference answer embedding.
  - If similarity is $\ge 0.88$, immediately marks `correct = True, partial_credit = 1.0`.
  - If ambiguous ($0.40 \le \text{similarity} < 0.88$), dispatches to a constrained LLM judge with a strict rubric prompt emitting JSON:
    `{ "correct": bool, "partial_credit": float, "confidence": float, "feedback_text": str }`.

### Misconception Classification Taxonomies
For incorrect or partially correct answers, `ml_core` classifies the error against curated, subject-specific misconception inventories:
- **Physics**: *"Confuses velocity with acceleration"*, *"Assumes force is necessary for motion (Aristotelian trap)"*, *"Confuses electric potential with electric current"*.
- **Mathematics**: *"Ignores negative signs when squaring"*, *"Divides by zero implicitly"*, *"Confuses perimeter with area"*.
- **Computer Science**: *"Off-by-one loop boundary error"*, *"Confuses assignment (=) with equality (==)"*, *"Assumes recursion has no memory overhead"*.

The resulting `misconception_tag` directly drives the Adaptation Controller in `ai_agent_orchestration`.

### Visual-Type Suggester
A rule-based classification table mapping concepts and subjects to optimal visual modalities:
$$\text{Subject / Concept Type} \longrightarrow \text{visual\_type}$$
- Mathematics $\longrightarrow$ `equation` (LaTeX) or `graph` (Cartesian plots).
- Physics $\longrightarrow$ `diagram` (Free-body / circuits) or `simulation`.
- Biology / Chemistry $\longrightarrow$ `diagram` (Labeled anatomy / reaction flows).
- History / Literature $\longrightarrow$ `timeline` (Chronological sequence) or `map` (Geographic routes).
- Computer Science $\longrightarrow$ `code` (Syntax-highlighted terminal) or `diagram` (Architecture graphs).

---

## 3. What is Implemented Till Now (Current Status)

| Component | Specification & Implementation | Status |
|---|---|---|
| **Contract Schemas** | Authoritative schemas in `instructions/Contract.md` (§9 `StudentResponse`, §10 `EvaluationResult`, §5 `LessonPlan`). | **Contract-Locked & Verified** |
| **Module Instructions** | `instructions/overview.md`, `instructions/detail_plan.md`, `instructions/contract.md` detailing hybrid evaluation and misconception tagging. | **Complete** |
| **Directory Skeleton** | `src/` and `tests/` (`unit/`, `integration/`, `e2e/`) partitioned and prepared. | **Scaffolded** |
| **Answer Evaluator** | Two-stage hybrid evaluation engine scheduled for implementation in Phase 6. | **Next Immediate Sprint** |
| **Taxonomy Store** | Per-subject JSON misconception taxonomy files and classification prompts. | **Next Immediate Sprint** |
| **Visual Suggester** | Deterministic keyword and subject rule table with LLM fallback. | **Next Immediate Sprint** |

---

## 4. Full File Structure

```
modules/ml_core/
├── docs/
│   └── ml_core_detail.md                       # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Authoritative cross-module contract definitions
│   ├── detail_plan.md                          # Component specifications and evaluation algorithms
│   └── overview.md                             # High-level module mission statement
├── src/
│   ├── .gitkeep                                # Active source directory
│   ├── __init__.py                             # (Target architecture) Package exports
│   ├── evaluation/                             # (Target architecture)
│   │   ├── __init__.py                         # Exposes AnswerEvaluator
│   │   ├── evaluator.py                        # Master hybrid answer evaluator (Tier 1 Rule + Tier 2 Judge)
│   │   ├── mcq_scorer.py                       # Exact-match and distractor rule scorer
│   │   └── semantic_scorer.py                  # Embedding cosine similarity + LLM rubric judge
│   ├── misconceptions/                         # (Target architecture)
│   │   ├── __init__.py                         # Exposes MisconceptionClassifier
│   │   ├── classifier.py                       # Misconception classifier mapping errors to tags
│   │   └── taxonomies/                         # Hand-curated educational misconception dictionaries
│   │       ├── cs_taxonomies.json              # Common programming misconceptions
│   │       ├── math_taxonomies.json            # Algebra, calculus, and arithmetic traps
│   │       └── physics_taxonomies.json         # Mechanics, electricity, and thermodynamics traps
│   ├── models.py                               # (Target architecture) Pydantic schemas for EvaluationResult
│   ├── service.py                              # (Target architecture) MLCoreService unified facade
│   └── visuals/                                # (Target architecture)
│       ├── __init__.py                         # Exposes VisualTypeSuggester
│       └── suggester.py                        # Deterministic rule table mapping concepts to visual_type
└── tests/
    ├── e2e/
    │   └── .gitkeep                            # End-to-end evaluation benchmark suites
    ├── integration/
    │   └── .gitkeep                            # Integration tests with ai_agent_orchestration
    └── unit/
        └── .gitkeep                            # Unit tests for scoring logic and misconception matching
```

---

## 5. Detailed File Logic (Planned & Authoritative Architecture)

### Target Files in `src/`
- **`src/models.py`**:
  - Implements `EvaluationResult` strictly adhering to Contract §10:
    ```python
    class EvaluationResult(BaseModel):
        node_id: str
        correct: bool
        partial_credit: float = Field(..., ge=0.0, le=1.0)
        misconception_tag: Optional[str] = None
        confidence: float = Field(..., ge=0.0, le=1.0)
        feedback_text: str
    ```
- **`src/evaluation/evaluator.py`**:
  - Implements `AnswerEvaluator`:
    - Checks question type: if `mcq`, delegates to `mcq_scorer.py`.
    - If `short_answer` or `explain_in_own_words`, delegates to `semantic_scorer.py`.
    - If answer is incorrect or partial, invokes `misconceptions/classifier.py` to diagnose the error.
- **`src/evaluation/semantic_scorer.py`**:
  - Calculates cosine similarity against expected concept embeddings.
  - If threshold requires an LLM judge, executes a zero-temperature evaluation prompt ensuring objective scoring without grade inflation.
- **`src/misconceptions/classifier.py`**:
  - Compares student's erroneous reasoning against subject taxonomy JSON files using few-shot classification.
  - Returns standardized tags (e.g. `physics:force_velocity_confusion`).
- **`src/visuals/suggester.py`**:
  - Analyzes concept title, subject keywords, and chapter metadata.
  - Returns the recommended `visual_type` (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`) to guide lesson planning.
- **`src/service.py`**:
  - `MLCoreService` facade exposing `evaluate_response()`, `classify_misconception()`, and `suggest_visual_type()`.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Student submits answer via WebSocket / Backend]
                        |
                        v
    MLCoreService.evaluate_response(StudentResponse, expected_concept)
                        |
         +--------------+--------------+
         | Question Type == MCQ?       |
         +--------------+--------------+
           | YES                       | NO (Short Answer / Problem)
           v                           v
  [mcq_scorer.py]             [semantic_scorer.py]
  Exact rule match            1. Embedding cosine similarity check
  Zero latency                2. If ambiguous -> Constrained LLM Rubric Judge
           |                           |
           +--------------+------------+
                          |
                          v
               Is answer incorrect or partial?
                          |
          +---------------+---------------+
          | NO                            | YES
          v                               v
   [correct = True]            [misconceptions/classifier.py]
   [partial_credit = 1.0]      Matches reasoning against subject taxonomy
   [misconception_tag = None]  Identifies root misconception tag
          |                               |
          +---------------+---------------+
                          |
                          v
         Returns EvaluationResult (Contract §10)
           {node_id, correct, partial_credit, misconception_tag, feedback_text}
                          |
                          v
         [Relayed to AI Orchestration Adaptation Controller]
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Inbound** | `backend` (from `frontend`) | **Contract §9** (`StudentResponse`) | Receives student's raw answer string, response type, and timing. |
| **Inbound** | `ai_agent_orchestration` | **Contract §8** (`InteractionEvent`) | Receives question prompt, expected concept, and options. |
| **Outbound** | `ai_agent_orchestration` | **Contract §10** (`EvaluationResult`) | Dispatches grade, partial credit, and diagnosed `misconception_tag`. |
| **Outbound** | `ai_agent_orchestration` | **Contract §5** (`LessonPlan.visual_type`) | Suggests optimal visual type for each planned lesson node. |
| **Outbound** | `avatar_voice` | **Contract §6** (`visual_spec.type`) | Directly determines which visual renderer (`equation`, `code`, etc.) gets invoked. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`ml_core`** module provides dedicated intelligence for **Evaluate**:
- Once the student submits an answer to a **Question**, `ml_core` evaluates the response.
- It detects the underlying flaw in thinking (misconception) and packages it into an `EvaluationResult`.
- This result immediately triggers the **Adapt** stage in `ai_agent_orchestration`, enabling true individualized learning.

---

## 9. Critical Notes for Any LLM Agent Working on This Module

> [!IMPORTANT]
> **Strict Guardrails for LLM Agents:**
> 1. **Zero LLM Calls for MCQs**: Never invoke an LLM to grade a standard multiple-choice question. Always use rule-based string matching in `mcq_scorer.py` to eliminate latency and cost.
> 2. **Deterministic Grading**: All LLM judge calls in `semantic_scorer.py` must run at `temperature = 0.0` with strict JSON schema enforcement to ensure evaluation consistency.
> 3. **Never Fabricate Misconception Tags**: Misconception tags must follow the namespaced format (e.g. `subject:concept_error`). Always match against established taxonomy dictionaries in `src/misconceptions/taxonomies/` to allow the adaptation controller to trigger targeted remedies.
> 4. **Fixture-Based Unit Tests**: In accordance with `07_Test.md`, all unit tests in `modules/ml_core/tests/` must use offline fixtures or recorded evaluation mocks without making live network calls.
