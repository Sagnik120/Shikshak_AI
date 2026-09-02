# detail_plan.md — ml_core

## Goal
Provide the ML building blocks that are cheaper/more reliable as dedicated models/heuristics
than as raw LLM calls: document parsing/structure extraction, answer evaluation, misconception
classification, visual-type suggestion.

## Components
1. **Document Parser** (`rag` calls this, or lives jointly — clarify boundary in Contract if
   duplicated): `pypdf`/`python-docx`/`python-pptx` → plain text + structural hints (headings,
   slide titles, page numbers) → feeds `ParsedDocument.chunks`/`detected_structure`.
2. **Concept/Key-term extractor**: lightweight NER/keyphrase extraction (e.g.
   `sentence-transformers` + simple noun-phrase extraction, or an LLM call with a strict JSON
   schema) → populates `detected_structure.key_terms` and helps Planner pick lesson nodes.
3. **Answer Evaluator**: given `StudentResponse` + `expected_concept` (+ retrieved grounding
   chunk if available), classify correct/partial/incorrect. Hybrid approach:
   - MCQ: exact/rule match (fast, free, no hallucination risk).
   - Short-answer/free-text: embedding-similarity pre-filter + LLM judge with a constrained
     rubric prompt (return strict JSON: `correct`, `partial_credit`, `feedback_text`).
4. **Misconception Classifier**: for incorrect answers, map to a `misconception_tag` from a
   per-subject taxonomy (start with a small hand-curated taxonomy per common subject, e.g.
   physics: "confuses current with charge", "assumes Ohm's law linearity fails" — ref
   physics-education-research misconception inventories) using few-shot LLM classification;
   log new tags for later taxonomy growth (see Batch A in `new_phases.md`).
5. **Visual-Type Suggester**: rule table keyed by subject/concept-type (math→equation/graph,
   physics→diagram/simulation, biology→labeled diagram, history→timeline/map,
   programming→code/flow/architecture) with an LLM fallback for ambiguous concepts — output
   feeds `LessonPlan.nodes[].visual_type` and `TeachingSegment.visual_spec`.

## Design principle
Every function here must be independently unit-testable with fixture inputs (no live network
calls in unit tests — use recorded/mocked LLM responses per `07_Test.md`).
