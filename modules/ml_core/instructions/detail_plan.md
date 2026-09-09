# detail_plan.md — ml_core

## Goal
Provide specialized Machine Learning building blocks and deterministic heuristics that are cheaper, lower-latency, and more reliable than raw unconstrained LLM calls:
1. **Answer Evaluation** (Two-stage hybrid MCQ + semantic freeform evaluation)
2. **Misconception Classification** (Curated per-subject educational taxonomies)
3. **Concept & Key-Term Extraction** (Lightweight keyword/phrase extraction for lesson node indexing)
4. **Visual-Type Suggestion** (Deterministic keyword-to-visual heuristics with LLM fallback)
5. **Isolated Module Web Testbed & Hierarchical Traceability Logger** (Interactive diagnostic studio on Port 8003)

---

## 1. Production Architecture & Implemented Components

### 1.1 Answer Evaluation Engine (`src/answer_evaluation/`)
- **`mcq_evaluator.py` (`MCQEvaluator`)**:
  - Pure deterministic comparison between `StudentResponse.raw_answer` and `expected_concept` / answer key.
  - Case-insensitive, stripped string equality check.
  - Latency: < 1ms; Token Cost: 0; Hallucination Risk: 0%.
  - Emits Contract §10 `EvaluationResult(correct=bool, partial_credit=1.0 or 0.0, confidence=1.0)`.
- **`freeform_evaluator.py` (`FreeformEvaluator`)**:
  - Two-stage hybrid evaluation for conceptual/short answers:
    - **Stage 1 (Embedding Cosine Similarity)**: Computes vector cosine similarity between student text and reference answer.
      - High confidence ($\ge 0.88$): Immediately marks `correct=True, partial_credit=1.0, confidence=0.95`.
      - Low confidence ($< 0.40$): Immediately marks `correct=False, partial_credit=0.0, confidence=0.90`.
    - **Stage 2 (Constrained LLM Judge)**: If ambiguous ($0.40 \le \text{similarity} < 0.88$), calls Gemini with a strict rubric prompt enforcing deterministic zero-temperature JSON output:
      `{"correct": bool, "partial_credit": float, "confidence": float, "feedback_text": str}`.

### 1.2 Misconception Classifier (`src/misconception/`)
- **`classifier.py` (`MisconceptionClassifier`)**:
  - For incorrect or partially correct student answers, maps student reasoning to authoritative pedagogical error tags.
  - Curated taxonomy files in `taxonomies/`:
    - `physics_taxonomies.json`: Traps like `physics:force_velocity_confusion`, `physics:current_consumption`, `physics:gravity_mass_proportionality`.
    - `math_taxonomies.json`: Traps like `math:sign_error_squaring`, `math:divide_by_zero`, `math:perimeter_area_confusion`.
    - `cs_taxonomies.json`: Traps like `cs:off_by_one`, `cs:assignment_vs_equality`, `cs:recursion_no_base_case`.
  - Classification flow:
    1. Loads subject taxonomy.
    2. Runs few-shot JSON prompt with Gemini adapter.
    3. Validates output tag against allowed taxonomy keys; falls back to `{subject}:general_conceptual_gap` if unrecognized.

### 1.3 Concept & Key-Term Extractor (`src/concept_extraction/`)
- **`extractor.py` (`ConceptExtractor`)**:
  - Extracts key technical phrases and conceptual entities from educational chunks/documents without requiring heavy LLM inference.
  - Uses tokenization, stopword filtering, and frequency/n-gram scoring.
  - Outputs structured `ConceptChunk` objects containing `term`, `importance_score`, and `character_offsets` for Planner node generation.

### 1.4 Visual-Type Suggester (`src/visual_suggestion/`)
- **`suggester.py` (`VisualTypeSuggester`) & `rules.py`**:
  - Maps subjects and pedagogical concept types to Contract §5 / Contract §6 `VisualType` (`equation`, `graph`, `diagram`, `code`, `timeline`, `map`):
    - Math / Calculus $\to$ `equation` or `graph`
    - Physics / Circuits $\to$ `diagram` or `simulation`
    - Biology / Botany $\to$ `diagram`
    - History / Chronology $\to$ `timeline` or `map`
    - Computer Science / Algorithms $\to$ `code` or `diagram`
  - Fallback: Calls Gemini LLM judge only when ambiguous concepts do not match heuristic tables.

### 1.5 Unified Service Facade (`src/service.py`)
- **`MLCoreService`**:
  - Unified interface exposing:
    - `evaluate_answer(response: StudentResponse, expected: str, subject: str) -> EvaluationResult`
    - `classify_misconception(student_answer: str, question: str, subject: str) -> Optional[str]`
    - `extract_concepts(text: str, top_k: int) -> List[ConceptChunk]`
    - `suggest_visual(concept: str, subject: str) -> VisualType`
  - Adheres strictly to Contract §9 (`StudentResponse`) and Contract §10 (`EvaluationResult`).

---

## 2. Interactive Web Testbed & Isolated Diagnostic Environment

### 2.1 Dedicated Testbed Server (`tests/web_test/server.py`)
- **Port Allocation**: Runs on **Port 8003** (leaving Port 8000 production backend untouched).
- **FastAPI Endpoints**:
  - `GET /`: Serves the light professional diagnostic studio.
  - `GET /api/test/status`: Health check, uptime, module version, and active subsystem checklist.
  - `POST /api/test/evaluate`: Executes `MLCoreService.evaluate_answer` with timing, tracing, and logging.
  - `POST /api/test/misconception`: Executes `MisconceptionClassifier.classify` against subject taxonomies.
  - `POST /api/test/concepts`: Extracts key phrases from submitted educational text.
  - `POST /api/test/visual_suggestion`: Evaluates heuristic rule table with fallback to LLM.
  - `GET /api/test/logs`: Lists categorized test logs.
  - `GET /api/test/logs/{category}/{filename}`: Retrieves raw JSON or formatted text execution log.

### 2.2 Hierarchical Logging & Hallucination Traceability (`tests/web_test/logger.py`)
- **Category-Partitioned Log Directory**:
  ```
  modules/ml_core/tests/web_test/logs/
  ├── evaluation/     # Dual .json and .log files for answer evaluation runs
  ├── misconception/  # Dual .json and .log files for misconception diagnosis runs
  ├── concepts/       # Dual .json and .log files for concept extraction runs
  ├── visuals/        # Dual .json and .log files for visual type suggestions
  ├── service/        # Lifecycle and facade dispatch logs
  └── errors/         # Unhandled exceptions, validation errors, and malformed inputs
  ```
- **Traceability Metadata Per Log Entry**:
  - `timestamp_iso`: Exact execution timestamp in UTC/ISO-8601.
  - `calling_file`: Exact Python file (e.g., `evaluator.py`, `freeform_evaluator.py`, `classifier.py`).
  - `calling_function`: Exact function/method invoked (e.g., `_evaluate_freeform`, `classify_with_llm`).
  - `execution_latency_ms`: Real-time execution duration in milliseconds.
  - `input_payload`: Raw input parameters provided by the user.
  - `output_payload`: Complete result emitted by the module.
  - `is_hallucination_suspect`: Heuristic flag triggered if LLM judge outputs invalid JSON, out-of-range confidence, or ungrounded tags.

### 2.3 Light Professional UI (`tests/web_test/static/`)
- **Visual Design Rules**:
  - **Strict Light Theme**: Clean white background (`#ffffff`), soft slate page surface (`#f8fafc`), crisp borders (`#e2e8f0`).
  - **No Dark Mode**: Absolutely zero dark background surfaces or low-contrast dark themes.
  - **Typography**: Clean modern sans-serif typography (`Inter`, `system-ui`).
  - **Interactive Presets**: Instant one-click test cases for Physics, Math, Computer Science, and Biology.
  - **Log Viewer**: Collapsible JSON inspector and formatted trace viewer with latency badges and calling function tags.

---

## 3. Verification & Testing Standards
1. **Unit Testing**: All algorithms tested in `modules/ml_core/tests/unit/` using offline mocks and deterministic assertions (`07_Test.md`).
2. **Integration Testing**: Boundary validation with `ai_agent_orchestration` and `rag` in `modules/ml_core/tests/integration/`.
3. **Web Test Server Testing**: Dedicated automated pytest suite in `modules/ml_core/tests/unit/test_ml_core_web_test_server.py`.
4. **Git Hygiene**: Runtime `*.log` and `*.json` test logs excluded via `.gitignore`; subdirectories preserved via `.gitkeep`.
