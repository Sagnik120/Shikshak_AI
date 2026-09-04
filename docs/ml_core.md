# ML Core - Implementation Documentation

## 1. Module Purpose
The `ml_core` module handles the evaluation of student responses, classification of misconceptions, extraction of concepts from RAG documents, and determination of visual heuristics. It uses deterministic rules where possible (e.g., MCQ evaluations, rule-table visuals) and hybrid LLM/embedding fallback only when necessary.

## 2. File Structure
```
modules/ml_core/src/
├── adapters/
│   └── llm_adapter_client.py       # Wrapper for Orchestration's LLMAdapter
├── answer_evaluation/
│   ├── evaluator.py                # Base/Dispatcher evaluator
│   ├── mcq_evaluator.py            # Deterministic MCQ matcher
│   └── freeform_evaluator.py       # Hybrid embedding/LLM judge
├── concept_extraction/
│   ├── config.py                   # NLP configurations (stopwords)
│   └── extractor.py                # TF-based key_term extractor
├── embeddings/
│   └── embedding_client.py         # sentence-transformers wrapper
├── misconception/
│   ├── classifier.py               # LLM taxonomy mapper
│   └── taxonomy_loader.py          # JSON taxonomy loader
├── schemas/
│   └── evaluation.py               # EvaluationResult schema
├── visual_suggestion/
│   ├── rules.py                    # Deterministic subject->visual mappings
│   └── suggester.py                # Rule engine + LLM fallback
└── service.py                      # Public MLCoreService facade
```

## 3. Answer Evaluation
### MCQ Path (`mcq_evaluator.py`)
- **Inputs**: raw_answer, expected_concept.
- **Logic**: 100% deterministic, case-insensitive, stripped string matching. 
- **LLM/Embeddings**: ZERO calls made.

### Free-text Path (`freeform_evaluator.py`)
- **Inputs**: raw_answer, expected_concept.
- **Logic**: Hybrid architecture using `sentence-transformers` for cosine similarity.
  - Similarity > 0.8: Auto-scored as Correct (bypass LLM).
  - Similarity < 0.3: Auto-scored as Incorrect (bypass LLM).
  - Similarity 0.3 - 0.8: Triggers LLM judge to output valid JSON `correct`, `partial_credit`, and `feedback_text`.
- **Output**: `EvaluationResult` (Contract §10).

## 4. Concept Extraction (`extractor.py`)
- **Boundary**: Does NOT read raw bytes or PDFs. Strictly consumes chunk texts from RAG's `ParsedDocument`.
- **Algorithm**: Zero-LLM Term Frequency (TF) word counts, filtered by a custom stopwords list (`config.py`).
- **Output**: List of string key terms.

## 5. Misconception Classifier (`classifier.py`)
- **Taxonomy**: Loaded from `modules/ml_core/tests/fixtures/taxonomy_fixtures/physics.json` during testing. 
- **Flow**: If the subject exists, the LLM maps the incorrect answer to a predefined `tag`. 
- **Unclassified**: If the LLM hallucinates an unknown tag or the subject isn't mapped, it returns `None`.

## 6. Visual-Type Suggester (`suggester.py`)
- **Rules**: Checks deterministic mappings first (e.g., `math` → `equation`, `history` → `timeline`).
- **Fallback**: Uses LLM to pick a visual type strictly from the Contract §5 Enum (`equation|graph|diagram|code|image|timeline|map|simulation`).

## 7. Service / Public Interface (`service.py`)
- `MLCoreService` exposes `evaluate_answer`, `extract_concepts`, and `suggest_visual_type`.
- Mirrors the exact stub expectations in `ai_agent_orchestration/src/integration/ml_core_client.py`.

## 8. Dependencies & Testing
- **Dependencies**: `sentence-transformers` is required for freeform evaluation. `LLMAdapter` is imported via a client facade to reuse Orchestration's logic.
- **Tests**: 20 isolated unit and integration tests.
- **Test Strategy**: Embedding calls are entirely mocked using `unittest.mock.patch` to prevent auto-downloading models during test execution. `FakeLLMAdapter` is reused from Orchestration to verify JSON handling without network calls.
- **Results**: 20/20 tests collected cleanly.

## 9. Known Limitations
- Taxonomy JSON files only contain a demo `physics.json` taxonomy. Expanding this requires populating the taxonomy directory.
- Requires Backend integration to connect user interactions to `MLCoreService.evaluate_answer()`.
