# ML Core Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `ml_core`  
> **Repository Path**: `modules/ml_core/`  
> **Primary Role**: Student Response Evaluation, Misconception Taxonomy Classification, Key-Term Extraction & Visual Type Heuristics  
> **Status**: **IMPLEMENTED & VERIFIED** (28 unit/integration tests passing; isolated web testbed active on Port 8003)  
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
  - Implemented in `src/answer_evaluation/mcq_evaluator.py`.
  - For multiple-choice questions, compares `StudentResponse.raw_answer` directly with `expected_concept` or answer keys using case-insensitive normalization.
  - Zero latency (< 1ms), zero token cost, and 100% deterministic accuracy (zero hallucination risk).
- **Tier 2 (Embedding Cosine Similarity + Constrained LLM Judge for Free-Text)**:
  - Implemented in `src/answer_evaluation/freeform_evaluator.py`.
  - For short-answer and conceptual questions, first runs cosine similarity between the student's answer embedding and the reference answer embedding.
  - If similarity is $\ge 0.88$, immediately marks `correct = True, partial_credit = 1.0, confidence = 0.95`.
  - If similarity is $< 0.40$, immediately marks `correct = False, partial_credit = 0.0, confidence = 0.90`.
  - If ambiguous ($0.40 \le \text{similarity} < 0.88$), dispatches to a constrained LLM judge with a strict rubric prompt emitting JSON:
    `{ "correct": bool, "partial_credit": float, "confidence": float, "feedback_text": str }`.

### Misconception Classification Taxonomies
Implemented in `src/misconception/classifier.py`. For incorrect or partially correct answers, `ml_core` classifies the error against curated, subject-specific misconception inventories:
- **Physics (`physics_taxonomies.json`)**: *"Confuses velocity with acceleration"*, *"Assumes force is necessary for motion (Aristotelian trap)"*, *"Confuses electric potential with electric current"*.
- **Mathematics (`math_taxonomies.json`)**: *"Ignores negative signs when squaring"*, *"Divides by zero implicitly"*, *"Confuses perimeter with area"*.
- **Computer Science (`cs_taxonomies.json`)**: *"Off-by-one loop boundary error"*, *"Confuses assignment (=) with equality (==)"*, *"Assumes recursion has no memory overhead"*.

The resulting `misconception_tag` directly drives the Adaptation Controller in `ai_agent_orchestration`.

### Visual-Type Suggester
Implemented in `src/visual_suggestion/suggester.py` & `rules.py`. A rule-based classification table mapping concepts and subjects to optimal visual modalities:
$$\text{Subject / Concept Type} \longrightarrow \text{visual\_type}$$
- Mathematics $\longrightarrow$ `equation` (LaTeX) or `graph` (Cartesian plots).
- Physics $\longrightarrow$ `diagram` (Free-body / circuits) or `simulation`.
- Biology / Chemistry $\longrightarrow$ `diagram` (Labeled anatomy / reaction flows).
- History / Literature $\longrightarrow$ `timeline` (Chronological sequence) or `map` (Geographic routes).
- Computer Science $\longrightarrow$ `code` (Syntax-highlighted terminal) or `diagram` (Architecture graphs).
### Dual Execution Architecture & Live Gemini Adapter Integration
The module is designed for dual-mode execution without code modifications:
- **Live Production Mode (`GeminiLLMAdapter`)**:
  - Automatically activated when `GEMINI_API_KEY` is present in the root `.env` or system environment.
  - Connects to Google Gemini API (`gemini-2.0-flash` with fallback to `gemini-1.5-flash`).
  - Used for:
    1. **Freeform Rubric Judge**: Zero-temperature JSON evaluation of ambiguous short answers.
    2. **Misconception Classifier Fallback**: Few-shot classification when heuristic taxonomy match is uncertain.
    3. **Visual Suggester Fallback**: Semantic modality resolution when concepts fall outside `rules.py`.
- **Deterministic Offline / CI Mode (`SmartMockLLMAdapter`)**:
  - Automatically engaged when no API key is provided or during headless unit testing.
  - Generates Contract-compliant, deterministic JSON responses with zero network calls and zero cost.
- **Auto-Environment Ingestion**:
  - The factory function `get_llm_adapter()` automatically executes `_load_env()` to parse `.env` at the project root before checking environment variables.
  - The standalone testbed server (`server.py`) additionally calls `load_dotenv()` on startup to ensure all model parameters are loaded.

---

## 3. What is Implemented Till Now (Current Status)

| Component | Specification & Implementation | Status |
|---|---|---|
| **Contract Schemas** | Authoritative schemas in `instructions/Contract.md` (§9 `StudentResponse`, §10 `EvaluationResult`, §5 `LessonPlan`, §6 `TeachingSegment`). | **Contract-Locked & Verified** |
| **Module Instructions** | `instructions/overview.md`, `instructions/detail_plan.md`, `instructions/contract.md` detailing hybrid evaluation and misconception tagging. | **Complete & Synchronized** |
| **Answer Evaluators** | `MCQEvaluator` (rule-based) & `FreeformEvaluator` (embedding cosine similarity + Gemini LLM judge). | **Fully Implemented & Verified** |
| **Misconception Classifier** | Taxonomy-backed JSON matching for Physics, Math, CS with few-shot LLM fallback. | **Fully Implemented & Verified** |
| **Concept Extractor** | Lightweight key-term & entity extraction emitting scored `ConceptChunk` objects. | **Fully Implemented & Verified** |
| **Visual Suggester** | Rule table with LLM fallback mapping concepts to Contract §5 visual modalities. | **Fully Implemented & Verified** |
| **MLCoreService Facade** | Unified orchestration entrypoint exposing all core evaluation and classification capabilities. | **Fully Implemented & Verified** |
| **Web Testbed Studio** | Standalone FastAPI diagnostic server on **Port 8003** with pure light professional UI and hierarchical logging. | **Fully Implemented & Verified** |
| **Test Suite** | Comprehensive pytest suite across unit, integration, and web test server (28 passing tests). | **100% Passing (28/28)** |

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
│   ├── __init__.py                             # Package exports
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── llm.py                              # LLM adapter interface
│   ├── answer_evaluation/
│   │   ├── __init__.py                         # Exposes MCQEvaluator and FreeformEvaluator
│   │   ├── freeform_evaluator.py               # Embedding cosine similarity + Gemini rubric judge
│   │   └── mcq_evaluator.py                    # Exact-match string rule scorer (< 1ms latency)
│   ├── concept_extraction/
│   │   ├── __init__.py                         # Exposes ConceptExtractor
│   │   └── extractor.py                        # Lightweight key-term and entity extractor
│   ├── embeddings/
│   │   ├── __init__.py                         # Fast embedding utilities
│   │   └── local_embeddings.py                 # Cosine similarity and vector representation
│   ├── misconception/
│   │   ├── __init__.py                         # Exposes MisconceptionClassifier
│   │   ├── classifier.py                       # Taxonomy-backed misconception diagnostic classifier
│   │   └── taxonomies/                         # Curated pedagogical misconception dictionaries
│   │       ├── cs_taxonomies.json              # Programming misconception catalog
│   │       ├── math_taxonomies.json            # Algebra and calculus misconception catalog
│   │       └── physics_taxonomies.json         # Mechanics and circuits misconception catalog
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── concept.py                          # ConceptChunk schema
│   │   ├── evaluation.py                       # EvaluationResult (Contract §10) and StudentResponse (§9)
│   │   └── visual.py                           # VisualType enum and suggestion schemas
│   ├── service.py                              # MLCoreService unified facade
│   └── visual_suggestion/
│       ├── __init__.py                         # Exposes VisualTypeSuggester
│       ├── rules.py                            # Subject and keyword rule mappings
│       └── suggester.py                        # Heuristic recommender with LLM fallback
└── tests/
    ├── e2e/
    │   └── .gitkeep                            # End-to-end evaluation benchmark suites
    ├── fixtures/                               # Mock responses and sample student inputs
    ├── integration/
    │   ├── test_ml_core_service_contract.py    # Service facade contract verification
    │   ├── test_orchestration_boundary.py      # Orchestrator boundary tests
    │   └── test_rag_boundary.py                # RAG boundary tests
    ├── unit/
    │   ├── test_concept_extractor.py           # Unit tests for key-term extraction
    │   ├── test_freeform_evaluator.py          # Unit tests for two-stage freeform scoring
    │   ├── test_mcq_evaluator.py               # Unit tests for deterministic MCQ scoring
    │   ├── test_misconception_classifier.py    # Unit tests for taxonomy matching
    │   ├── test_ml_core_web_test_server.py     # Unit tests for web testbed REST server
    │   ├── test_schemas.py                     # Schema validation tests
    │   └── test_visual_suggester.py            # Unit tests for visual rule engine and fallback
    └── web_test/                               # Standalone Web Diagnostic Testbed (Port 8003)
        ├── logger.py                           # Hierarchical trace and hallucination logger
        ├── server.py                           # FastAPI testbed application
        ├── logs/                               # Categorized test trace output directory
        │   ├── concepts/                       # Concept extraction traces
        │   ├── errors/                         # Validation and exception traces
        │   ├── evaluation/                     # Answer evaluation traces
        │   ├── misconception/                  # Misconception classification traces
        │   ├── service/                        # Facade dispatch traces
        │   └── visuals/                        # Visual suggestion traces
        └── static/                             # Pure light professional frontend
            ├── css/
            │   └── style.css                   # Crisp light theme styling (NO dark mode)
            ├── js/
            │   └── app.js                      # Diagnostic studio interactive logic
            └── index.html                      # 5-tab diagnostic workbench
```

---

## 5. Detailed File Logic (Authoritative Codebase Implementation)

### `src/service.py` (`MLCoreService`)
- Serves as the primary public facade for all other modules (`ai_agent_orchestration`, `backend`).
- Methods:
  - `evaluate_answer(response: StudentResponse, expected_concept: str, subject: str = "general") -> EvaluationResult`:
    Dispatches to `MCQEvaluator` if `response.response_type == "mcq_choice"`, or `FreeformEvaluator` otherwise. If the answer is incorrect, automatically invokes `MisconceptionClassifier` to attach `misconception_tag`.
  - `classify_misconception(student_answer: str, question: str, subject: str) -> Optional[str]`:
    Directly invokes `MisconceptionClassifier`.
  - `extract_concepts(text: str, top_k: int = 5) -> List[ConceptChunk]`:
    Directly invokes `ConceptExtractor`.
  - `suggest_visual(concept: str, subject: str) -> str`:
    Directly invokes `VisualTypeSuggester`.

### `src/answer_evaluation/mcq_evaluator.py` (`MCQEvaluator`)
- Pure rule-based string comparison.
- Normalizes both `raw_answer` and `expected` by trimming whitespace and lowercasing.
- Emits `EvaluationResult(node_id, correct=bool, partial_credit=1.0 or 0.0, confidence=1.0, feedback_text=str)`.
- Never calls external APIs or LLMs.

### `src/answer_evaluation/freeform_evaluator.py` (`FreeformEvaluator`)
- Implements two-stage semantic evaluation:
  1. Computes cosine similarity between embeddings of `raw_answer` and `expected_concept`.
  2. If $\ge 0.88$: marks `correct=True, partial_credit=1.0, confidence=0.95`.
  3. If $< 0.40$: marks `correct=False, partial_credit=0.0, confidence=0.90`.
  4. If between $0.40$ and $0.88$: invokes LLM judge adapter with a strict JSON rubric prompt at `temperature=0.0`.

### `src/misconception/classifier.py` (`MisconceptionClassifier`)
- Reads curated taxonomy files from `src/misconception/taxonomies/`.
- Queries Gemini adapter with the student's answer, question, and subject taxonomy.
- Validates the returned tag against known taxonomy keys. If unmapped, defaults to `{subject}:general_conceptual_gap`.

### `src/concept_extraction/extractor.py` (`ConceptExtractor`)
- Tokenizes and cleans input educational text.
- Extracts meaningful technical keyphrases and ranked n-grams.
- Returns list of `ConceptChunk(term=str, score=float, start_char=int, end_char=int)`.

### `src/visual_suggestion/suggester.py` & `rules.py` (`VisualTypeSuggester`)
- Consults `SUBJECT_TO_VISUAL` and `CONCEPT_TO_VISUAL` rule dictionaries.
- If a match is found, immediately returns the deterministic `VisualType`.
- If unmatched, invokes Gemini LLM judge fallback with a constrained enum schema.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Student submits answer via WebSocket / Backend]
                        |
                        v
    MLCoreService.evaluate_answer(StudentResponse, expected_concept)
                        |
         +--------------+--------------+
         | Question Type == MCQ?       |
         +--------------+--------------+
           | YES                       | NO (Short Answer / Problem)
           v                           v
   [mcq_evaluator.py]          [freeform_evaluator.py]
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
   [correct = True]            [misconception/classifier.py]
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
> 1. **Zero LLM Calls for MCQs**: Never invoke an LLM to grade a standard multiple-choice question. Always use rule-based string matching in `mcq_evaluator.py` to eliminate latency and cost.
> 2. **Deterministic Grading**: All LLM judge calls in `freeform_evaluator.py` must run at `temperature = 0.0` with strict JSON schema enforcement to ensure evaluation consistency.
> 3. **Never Fabricate Misconception Tags**: Misconception tags must follow the namespaced format (e.g. `subject:concept_error`). Always match against established taxonomy dictionaries in `src/misconception/taxonomies/` to allow the adaptation controller to trigger targeted remedies.
> 4. **Fixture-Based Unit Tests**: In accordance with `07_Test.md`, all unit tests in `modules/ml_core/tests/` must use offline fixtures or recorded evaluation mocks without making live network calls.

---

## 10. Interactive Web Testbed & Hierarchical Traceability Engine (Port 8003)

To allow manual user testing and strict traceability without modifying the production backend on Port 8000, `ml_core` features a dedicated standalone testbed:

### 10.1 Dedicated Server Configuration
- **Server File**: `modules/ml_core/tests/web_test/server.py`
- **Network Port**: **`8003`** (Zero collision with production Port 8000, Orchestration Port 8001, RAG Port 8002, Avatar Port 8004)
- **Start Command**:
  ```bash
  ./.venv/bin/python modules/ml_core/tests/web_test/server.py
  ```
- **Web UI URL**: `http://localhost:8003/`

### 10.2 Hierarchical Logging Engine (`logger.py`)
Every operation executed via the testbed generates dual log files:
1. A structured JSON manifest (`.json`) containing parsed request payloads, responses, latency, calling `.py` file, and calling function.
2. A human-readable execution transcript (`.log`) formatted for quick visual inspection.

Logs are cleanly organized into 6 dedicated categories:
- `logs/evaluation/`: Answer evaluation runs (MCQ rule matches, cosine similarity scores, LLM judge verdicts).
- `logs/misconception/`: Error taxonomy lookups, candidate matches, and diagnosed error tags.
- `logs/concepts/`: Key-term extraction inputs, scored chunks, and execution timing.
- `logs/visuals/`: Subject/keyword rule resolutions and fallback LLM suggestions.
- `logs/service/`: High-level facade dispatch events.
- `logs/errors/`: Full stack traces, Pydantic validation errors, and malformed inputs.

### 10.3 Hallucination Detection & Traceability
To ensure complete debugging transparency and catch any hallucinating prompt or function:
- Every log record explicitly captures `calling_file` (e.g. `freeform_evaluator.py`, `classifier.py`) and `calling_function` (e.g. `_evaluate_freeform`, `classify_with_llm`).
- If an LLM judge emits an invalid schema, an out-of-range confidence score, or an unmapped misconception tag, the logger flags `is_hallucination_suspect: True` and records the exact trigger in `logs/errors/`.

### 10.4 Pure Light Professional Frontend
- **Design Aesthetic**: Crisp white `#ffffff` cards on a soft slate `#f8fafc` surface with slate-200 borders and vibrant indigo/emerald accents.
- **Strict Prohibition**: Strictly no dark mode or dark background surfaces.
- **Features**:
  - 5 dedicated workspaces: **Answer Evaluation**, **Misconception Classifier**, **Concept Extractor**, **Visual Suggester**, and **Structured Log Explorer**.
  - One-click subject presets for Physics, Mathematics, Computer Science, and Biology.
  - Live execution latency counters, confidence progress bars, and an interactive log inspector.

### 10.5 Live Adapter Status & Diagnostic Verification
The testbed dynamically verifies live production readiness vs offline test mode:
- The endpoint `GET /api/test/status` inspects the active adapter class name and returns:
  `{"status": "ready", "llm_adapter": "GeminiLLMAdapter", ...}` when `GEMINI_API_KEY` is loaded from `.env`.
- The web UI header displays a status badge indicating whether evaluations are utilizing the live Gemini LLM API or the deterministic SmartMock fallback.

