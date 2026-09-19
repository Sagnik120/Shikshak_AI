# ML Core Web Test Details

## 1. Purpose
This document provides the definitive manual web-test specification for the Shikshak AI ML Core module. It defines exactly what a human tester should enter into the isolated ML Core web testbed (`Port 8003`), the expected outputs, PASS/FAIL criteria, and the distinction between deterministic/local execution and LIVE Gemini LLM fallback paths. 

## 2. Scope and Production-Parity Principle
The web testbed directly invokes the **production `MLCoreService`** methods and uses the actual `LLMAdapter` and `EmbeddingClient` dependencies. The primary goal of these isolated tests is to prove that the core logical algorithms (Answer Evaluation, Concept Extraction, Misconception Classification, Visual Suggestion) behave correctly before integrating them into the full Shikshak AI web application pipeline.

If functionality passes here using the real dependencies, it is expected to pass end-to-end, except for downstream orchestration/rendering boundaries.

## 3. Test Environment
* **Environment:** Local web testbed on port `8003`.
* **Models:** Local `sentence-transformers` for embeddings (e.g., `all-MiniLM-L6-v2`); TF-IDF heuristics for concept extraction.
* **LLM Adapter:** `GeminiLLMAdapter` (which consumes the `.env` API key when invoked).
* **Logging:** Structured logs stored in `modules/ml_core/tests/web_test/logs/`.

## 4. Execution Modes
* **Local/Deterministic:** Validates fast embedding similarity, keyword heuristics, exact MCQ matching, and predefined taxonomy rules. **No API keys consumed.**
* **LIVE Gemini:** Validates complex semantic freeform judging and fallback classification paths. **Requires a valid `.env` Gemini API key (but MUST NOT log it).**
* **Full E2E:** Out of scope for this isolated testbed; involves Frontend -> Backend -> Orchestrator -> ML Core.

## 5. Web-Test Components
The web testbed contains tabs for:
1. Answer Evaluation
2. Misconception Classifier
3. Concept Extractor
4. Visual Suggester
5. Structured Log Explorer

---

## 6. Answer Evaluation Test Cases

* **Web Entry:** Answer Evaluation Tab -> `POST /api/test/evaluate`
* **Production Function:** `MLCoreService.evaluate_answer` -> `FreeformEvaluator.evaluate` (or `evaluate_mcq`)
* **Output Contract:** `EvaluationResult` Schema (JSON)

### A-01: Clearly Correct Freeform Answer
* **Execution Mode:** Local / Deterministic (High Similarity)
* **Input:**
  * Node ID: `node_01` | Response Type: `freeform`
  * Expected Concept: `Newton's Second Law describes the relationship between net force, mass, and acceleration (F=ma).`
  * Student Answer: `Newton's second law is F = ma, linking mass, force, and acceleration.`
* **Expected Output:**
  * `correct`: `true`
  * `confidence`: > 0.8
  * `feedback_text`: "Excellent! Your answer is spot on."
* **PASS Criteria:** Valid JSON schema is returned, skipping the LLM judge due to high embedding similarity.

### A-02: Exact Correct Answer (MCQ)
* **Execution Mode:** Local / Deterministic
* **Input:**
  * Node ID: `node_02` | Response Type: `mcq`
  * Expected Concept: `Option C`
  * Student Answer: `Option C`
* **Expected Output:** `correct`: `true`

### A-03: Clearly Incorrect Answer
* **Execution Mode:** Local / Deterministic (Low Similarity)
* **Input:**
  * Node ID: `node_03` | Response Type: `freeform`
  * Expected Concept: `Mitochondria is the powerhouse of the cell.`
  * Student Answer: `Gravity pulls apples down.`
* **Expected Output:**
  * `correct`: `false`
  * `confidence`: > 0.7 (i.e. `1.0 - similarity`)
* **PASS Criteria:** Bypasses LLM due to extremely low semantic similarity (below `0.3`).

### A-04: Partially Correct Answer (LIVE GEMINI)
* **Execution Mode:** LIVE GEMINI REQUIRED
* **Input:**
  * Node ID: `node_04` | Response Type: `freeform`
  * Expected Concept: `Photosynthesis converts carbon dioxide and water into glucose and oxygen.`
  * Student Answer: `Plants make their own food using sunlight and water.`
* **Expected Output:**
  * `correct`: `false` (or `true` depending on prompt strictness)
  * `partial_credit`: > `0.0`
* **PASS Criteria:** LLM judge triggers because embedding similarity is mid-range. Valid JSON is returned with partial credit.

### A-05: Semantically Correct but Lexically Different
* **Execution Mode:** Local or LIVE GEMINI
* **Input:**
  * Node ID: `node_05` | Response Type: `freeform`
  * Expected Concept: `Current is directly proportional to voltage when resistance is constant.`
  * Student Answer: `If voltage goes up while resistance stays the same, the current will also go up by the same ratio.`
* **PASS Criteria:** Recognized as substantially correct (`correct=true`), whether caught by embeddings or LLM judge.

### A-06: Correct Concept + Irrelevant Extra Information
* **Execution Mode:** LIVE GEMINI REQUIRED
* **Input:** Same expected concept as A-05. Student Answer: `Current goes up with voltage. Also my dog is brown.`
* **PASS Criteria:** Should not automatically become incorrect. Evaluated as partially or fully correct based on semantic intent.

### A-07: Empty Student Answer
* **Execution Mode:** Local / Deterministic
* **Input:** Student Answer: ` `
* **PASS Criteria:** Controlled validation error or safe classification as incorrect. Server must not crash.

### A-13: LIVE GEMINI Judge Test (Ambiguous)
* **Execution Mode:** LIVE GEMINI REQUIRED
* **Input:**
  * Node ID: `node_ambig` | Response Type: `freeform`
  * Expected Concept: `The earth orbits the sun due to gravitational pull.`
  * Student Answer: `The sun pulls the earth so it spins around.`
* **PASS Criteria:** The Gemini API executes successfully, returns the required JSON structure (`correct`, `partial_credit`, `feedback_text`), and the output is successfully parsed into an `EvaluationResult` without JSON decoding exceptions.

---

## 7. Misconception Classification Test Cases

* **Web Entry:** Misconception Tab -> `POST /api/test/misconception`
* **Production Function:** `MLCoreService.classify_misconception` -> `MisconceptionClassifier.classify`
* **Output Contract:** Misconception tag string or `null`.

### M-01: Clear Known Misconception (LIVE GEMINI)
* **Execution Mode:** LIVE GEMINI REQUIRED
* **Input:**
  * Subject: `physics`
  * Expected Concept: `All objects fall at the same rate in a vacuum.`
  * Student Answer: `Heavier objects fall faster because gravity pulls them more.`
* **Expected Output:** Tag matching a known physics taxonomy category (e.g., `gravity-mass-dependence`).
* **PASS Criteria:** The LLM successfully classifies the text into an allowed taxonomy tag.

### M-03: Correct Student Answer
* **Execution Mode:** LIVE GEMINI REQUIRED
* **Input:** Student Answer: `Objects in freefall experience equal acceleration.`
* **Expected Output:** `null` or "no misconception".

### M-08: Wrong Subject/Taxonomy Combination
* **Execution Mode:** Local / Deterministic
* **Input:** Subject: `invalid_subject`
* **PASS Criteria:** Controlled error indicating the taxonomy could not be loaded, rather than silent failure.

---

## 8. Concept Extraction Test Cases

* **Web Entry:** Concept Extractor Tab -> `POST /api/test/concepts`
* **Production Function:** `MLCoreService.extract_concepts` -> `ConceptExtractor.extract`
* **Output Contract:** `List[str]`

### C-01: Normal Educational Text
* **Execution Mode:** Local / Deterministic (TF-IDF Heuristic)
* **Input:** Chunk text containing "force", "mass", "acceleration". Top-K = `5`.
* **Expected Output:** List of top 5 keywords.
* **PASS Criteria:** Educational terms surface accurately; stopwords (e.g., "the", "and") are ignored.

### C-08: Empty Input
* **Execution Mode:** Local / Deterministic
* **Input:** Chunk text: ` `
* **PASS Criteria:** Returns an empty list `[]` without crashing.

### C-11: Mathematical/Physics Notation
* **Execution Mode:** Local / Deterministic
* **Input:** Chunk text: `F = ma represents Newton's second law.`
* **PASS Criteria:** Safely tokenizes symbols without regex crashes.

---

## 9. Visual Suggestion Test Cases

* **Web Entry:** Visual Suggester Tab -> `POST /api/test/visual_suggestion`
* **Production Function:** `MLCoreService.suggest_visual_type` -> `VisualTypeSuggester.suggest`
* **Output Contract:** String (e.g., `diagram`, `equation`, `avatar_only`)

### V-01: Known Deterministic Subject/Concept
* **Execution Mode:** Local / Deterministic
* **Input:** Subject: `math`, Concept: `quadratic formula derivation`
* **Expected Output:** `equation` or `diagram` based on `rules.py`.
* **PASS Criteria:** Bypasses LLM due to matching explicit fallback rules.

### V-07: LIVE GEMINI Visual Classification
* **Execution Mode:** LIVE GEMINI REQUIRED
* **Input:** Subject: `history`, Concept: `The fall of the Roman Empire`
* **Expected Output:** `diagram` or `avatar_only`.
* **PASS Criteria:** LLM responds with a valid classification that conforms to the allowed internal enum/modality string.

---

## 10. Structured Logging Test Cases

### L-01 to L-06: Verification
* **Execution Mode:** Local
* **Tests:** Submit an evaluation -> check `GET /api/test/logs`.
* **PASS Criteria:**
  1. A new JSON log file appears in the UI.
  2. The log contains `input_payload`, `output_payload`, and timestamps.
  3. **CRITICAL:** NO `.env` variables or API keys are written to the logs.

---

## 11. Gemini-Dependent Test Matrix

| Test ID | Component | Gemini Required? | Human Live Test? | Expected Validation |
|---|---|:---:|:---:|---|
| A-04, A-13 | Freeform Judge | Yes | Yes | Valid JSON matching `EvaluationResult`, semantically appropriate grading. |
| M-01 | Misconception | Yes | Yes | Valid taxonomy tag returned from the physics list. |
| V-07 | Visual Sugg. | Yes | Yes | Valid fallback modality string returned. |
| C-01 | Concept Extract | No | No | Uses deterministic TF-IDF logic. |
| A-01, A-03 | Embedding Eval | No | No | Skips Gemini due to confident similarity thresholds. |

---

## 12. Edge/Error Cases

* **Timeout / Rate Limit (Gemini):** If the Gemini API is rate-limited during a LIVE test, the `LLMAdapter` should log the error and return a safe fallback result (e.g., `confidence=0.5, correct=False` per the implementation in `FreeformEvaluator`).
* **Malformed Schema (Gemini):** If Gemini returns markdown instead of JSON, the `strip("`")` logic in `FreeformEvaluator` must clean it successfully.

---

## 13. Production-Parity Mapping

| Web Test Entry | Production Function | Output Contract | Downstream E2E Consumer |
|---|---|---|---|
| `POST /api/test/evaluate` | `MLCoreService.evaluate_answer` | `EvaluationResult` | `TeacherOrchestrator` (`EVALUATE` state) |
| `POST /api/test/misconception` | `MLCoreService.classify_misconception` | `Optional[str]` | `TeacherOrchestrator` (`ADAPT` state) |
| `POST /api/test/concepts` | `MLCoreService.extract_concepts` | `List[str]` | `RAGService` (Indexing prep) |
| `POST /api/test/visual_suggestion` | `MLCoreService.suggest_visual_type` | `str` | `AvatarVoiceService` |

---

## 14. Test Execution Order

1. **Phase 1 — Deterministic/Local:** Concept Extraction, extreme high/low similarity Answer Evaluation, deterministic Visual Suggestions, and error validation.
2. **Phase 2 — Real Gemini:** Freeform ambiguous LLM Judge (A-04), Misconception Classification (M-01), LLM Visual Suggestion (V-07).
3. **Phase 3 — Observability:** Structured logs checks (Verify no secrets leaked).
4. **Phase 4 — Full E2E:** Complete integration via the Orchestrator.

---

## 15. PASS/FAIL Recording Template

```text
Test ID:
Priority:
Component:
Execution Mode: [LOCAL / LIVE GEMINI]
Input:
Action:
Expected Output:
PASS Criteria:
FAIL Indicators:
Actual Result:
Status:
Notes:
```

---

## 16. Limitations and Remaining E2E Validation
Passing the isolated ML Core web test confirms that the algorithms, embedding clients, and LLM prompts produce the correct output contracts. 

**It DOES NOT prove:**
* That the Backend successfully serializes these Pydantic models for the Frontend.
* That the `TeacherOrchestrator` properly triggers these evaluations during active FSM transitions.
* That concurrent API limits won't crash the server under load.
These must be tested separately in the full web-app integration phase.
