# contract.md — ml_core (Module-Local Contract Specification)

This document formalizes how the `ml_core` module consumes, implements, and produces schemas defined in the root `instructions/Contract.md`, as well as internal data transfer models specific to `ml_core`.

---

## 1. Cross-Module Contract Interfaces

### 1.1 Inbound Interfaces
- **Contract §9: `StudentResponse`** (Produced by `frontend` / `backend`, consumed by `MLCoreService.evaluate_answer`):
  ```python
  class StudentResponse(BaseModel):
      session_id: str
      node_id: str
      raw_answer: str
      response_type: Literal["mcq_choice", "short_text", "voice_transcript"]
      response_time_sec: float
  ```

- **Contract §8: `InteractionEvent`** (Produced by `ai_agent_orchestration` during Question phase):
  - Provides question text, choices (for MCQ), reference answer / `expected_concept`, and target pedagogical node ID.

### 1.2 Outbound Interfaces
- **Contract §10: `EvaluationResult`** (Produced by `MLCoreService.evaluate_answer`, consumed by `ai_agent_orchestration` Adaptation Controller):
  ```python
  class EvaluationResult(BaseModel):
      node_id: str
      correct: bool
      partial_credit: float = Field(..., ge=0.0, le=1.0)
      misconception_tag: Optional[str] = None
      confidence: float = Field(..., ge=0.0, le=1.0)
      feedback_text: str
  ```

- **Contract §5: `VisualType`** (Produced by `VisualTypeSuggester`, consumed by `ai_agent_orchestration` Lesson Planner):
  ```python
  VisualType = Literal["equation", "graph", "diagram", "code", "timeline", "map"]
  ```

- **Contract §6: `TeachingSegment.visual_spec`** (Informed by `ml_core` visual recommendations, consumed by `avatar_voice` multimedia renderer):
  - Guides visual specification parameters (`title`, `layout`, `syntax`, `equations`).

### 1.3 Contract §14: `LLMAdapter` Interface & Dual-Mode Execution
- **Interface**:
  ```python
  class LLMAdapter(ABC):
      @abstractmethod
      def complete(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
          pass
  ```
- **Dual Implementations**:
  1. **`GeminiLLMAdapter` (Live API)**: Selected when `GEMINI_API_KEY` is present. Connects to `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent`.
  2. **`SmartMockLLMAdapter` (Deterministic Fallback)**: Selected in offline test fixtures or when no API key is available. Emits zero-cost Contract-compliant JSON fixtures.
- **Factory**: Instantiated via `get_llm_adapter()`, which automatically ingests `.env` before checking environment keys.

---

## 2. Module-Internal Data Models (`src/schemas/`)

These schemas are utilized internally within `modules/ml_core/` for sub-pipeline serialization:

- **`ConceptChunk`**:
  ```python
  class ConceptChunk(BaseModel):
      term: str
      score: float
      start_char: int
      end_char: int
  ```

- **`LLMJudgeRubricOutput`**:
  ```python
  class LLMJudgeRubricOutput(BaseModel):
      correct: bool
      partial_credit: float
      confidence: float
      feedback_text: str
  ```

- **`MisconceptionEntry`**:
  ```python
  class MisconceptionEntry(BaseModel):
      tag: str
      description: str
      remedial_strategy: str
  ```

---

## 3. Web Testbed REST API Contract (Port 8003)

The isolated diagnostic server exposes the following endpoints for validation:

| Endpoint | Method | Input Model | Output Model | Description |
|---|---|---|---|---|
| `/api/test/status` | `GET` | None | `Dict[str, Any]` | Health, uptime, active LLM adapter, and subsystem status |
| `/api/test/evaluate` | `POST` | `EvaluateRequest` | `EvaluationResult` + telemetry | Runs MCQ or Freeform evaluation |
| `/api/test/misconception` | `POST` | `MisconceptionRequest` | `Dict[str, Any]` | Classifies misconception tag |
| `/api/test/concepts` | `POST` | `ConceptsRequest` | `List[ConceptChunk]` | Extracts key phrases and scores |
| `/api/test/visual_suggestion`| `POST` | `VisualSuggestionRequest`| `Dict[str, str]` | Suggests optimal visual type |
| `/api/test/logs` | `GET` | Query `category` | `List[Dict[str, Any]]` | Lists execution log files |
| `/api/test/logs/{cat}/{fn}` | `GET` | Path params | Log content (JSON/text) | Inspects structured trace file |
