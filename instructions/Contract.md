# Contract.md — Cross-Module Data & API Contracts (ROOT, authoritative)

> Every module MUST implement/consume these exact shapes. Any change requires updating this
> file first, then notifying dependent modules via `06_Memory.md`. This is the single most
> important file in the repo for avoiding integration breakage between parallel-working agents.

## Naming Conventions
- JSON keys: `snake_case`. IDs: `<entity>_id` (string, UUID). Timestamps: ISO-8601 UTC.
- All monetary/time durations in **minutes** (`int`) unless suffixed `_sec`.

## 1. `UploadRequest` (Frontend → Backend)
```json
{
  "session_id": "string",
  "file": "<multipart file: pdf|docx|pptx|txt>",
  "constraints": { "$ref": "#/LearnerConstraints" }
}
```

## 2. `TopicRequest` (Frontend → Backend)
```json
{
  "session_id": "string",
  "topic": "string",
  "constraints": { "$ref": "#/LearnerConstraints" }
}
```

## 3. `LearnerConstraints`
```json
{
  "level": "beginner | intermediate | advanced",
  "language": "string (ISO 639-1 or name, e.g. 'hi', 'en', 'hinglish')",
  "time_budget_min": "int (e.g. 5, 20, 60; or 'multi_day_plan': true)",
  "style": "string | null  (e.g. 'exam-focused', 'story-driven')"
}
```

## 4. `ParsedDocument` (RAG → Backend/AI Orchestration)
```json
{
  "document_id": "string",
  "source_lang": "string",
  "chunks": [
    { "chunk_id": "string", "text": "string", "section_title": "string|null",
      "page_or_slide": "int|null", "embedding_ref": "string" }
  ],
  "detected_structure": { "chapters": ["string"], "key_terms": ["string"] }
}
```

## 5. `LessonPlan`
```json
{
  "lesson_id": "string",
  "source": "document | topic",
  "constraints": { "$ref": "#/LearnerConstraints" },
  "nodes": [
    { "node_id": "string", "concept": "string", "depth": "intro|core|advanced",
      "est_minutes": "int", "visual_type": "equation|graph|diagram|code|image|timeline|map|simulation",
      "checkpoint_question": "bool" }
  ]
}
```

## 6. `TeachingSegment` (AI Orchestration → Avatar/Voice)
```json
{
  "node_id": "string",
  "script_text": "string",
  "language": "string",
  "visual_spec": { "type": "string", "content": "string|object (e.g. LaTeX, code, image_prompt)" },
  "avatar_cue": "neutral|emphasis|questioning"
}
```

## 7. `RenderedVideoSegment` (Avatar/Voice → Backend/Frontend)
```json
{
  "node_id": "string", "video_url": "string", "duration_sec": "number",
  "captions_vtt_url": "string|null"
}
```

## 8. `InteractionEvent` (AI Orchestration → Frontend, via Backend WS)
```json
{
  "node_id": "string", "question_text": "string",
  "type": "mcq|short_answer|problem|application|explain_in_own_words",
  "options": ["string"] ,
  "expected_concept": "string"
}
```

## 9. `StudentResponse` (Frontend → Backend → ML Core)
```json
{ "node_id": "string", "raw_answer": "string", "response_type": "string", "response_time_sec": "number" }
```

## 10. `EvaluationResult` (ML Core → AI Orchestration)
```json
{
  "node_id": "string", "correct": "bool", "partial_credit": "number (0-1)",
  "misconception_tag": "string|null", "confidence": "number (0-1)",
  "feedback_text": "string"
}
```

## 11. `AdaptationDecision` (AI Orchestration internal, logged to Frontend right-panel)
```json
{ "action": "ALLOW|MODIFY|REGENERATE|HUMAN", "target_node_id": "string", "reason": "string" }
```

## 12. `AssessmentReport`
```json
{
  "lesson_id": "string", "score_pct": "number",
  "strong_areas": ["string"], "weak_areas": ["string"],
  "recommended_next": ["string"], "narrative_feedback": "string"
}
```

## 13. `LearnerProfile` (persisted, Backend-owned)
```json
{
  "learner_id": "string", "history": [ { "$ref": "#/AssessmentReport" } ],
  "strong_concepts": ["string"], "weak_concepts": ["string"],
  "current_learning_path": ["string"], "preferred_language": "string", "preferred_level": "string"
}
```

## 14. Adapter Interfaces (for swappable providers — do not hardcode a single vendor)
```
AvatarAdapter.render(script_text, language, avatar_cue) -> video_bytes|url
TTSAdapter.synthesize(text, language, voice_id) -> audio_bytes|url
VectorStoreAdapter.upsert(chunks) / .query(embedding, top_k) -> matches
LLMAdapter.complete(messages, tools?) -> response
```
Every module using an external AI service MUST go through the matching Adapter interface so the
underlying vendor can change without touching orchestration logic.

## Versioning
Prefix breaking changes with a version bump in the JSON, e.g. add `"contract_version": "v1"` to
top-level objects once the system stabilizes past Phase 2.
