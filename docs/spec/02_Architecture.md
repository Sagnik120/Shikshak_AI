# 02_Architecture.md — System Architecture & Data Contracts

## High-Level Data Flow
```
[Student Input]
   (a) Upload: PDF/DOCX/PPTX/Notes  --or--  (b) Topic string + constraints
        |
        v
 [Backend: Ingestion API] --(a)--> [RAG: Parse/Chunk/Embed] --> [Vector DB]
        |                                                            |
        +--(b, or a with retrieval)--> [AI Orchestration: Lesson Planner Agent]<--(retrieve)---+
                        |
                        v
             [Structured Lesson Plan JSON]  (see Contract: LessonPlan v1)
                        |
        +---------------+----------------+
        v                                 v
[AI Orchestration: Explainer Agent]   [ML Core: Visual Selector]
        |                                 |
        v                                 v
   [Script + Visual Spec] ---------> [Avatar/Voice: TTS + Avatar + Slide Render]
                        |
                        v
              [Rendered Teaching Video Segment] --> [Frontend: Video Player]
                        |
                        v
        [AI Orchestration: Questioner Agent] --> [Frontend: Interaction UI]
                        |
                        v (student answer)
        [ML Core: Answer Evaluator / Misconception Detector]
                        |
                        v
        [AI Orchestration: Adaptation Controller] --(ALLOW/MODIFY/REGENERATE/HUMAN)--> loop back to Explainer/Planner
                        |
                        v (lesson end)
        [AI Orchestration: Assessment Agent] --> [Learning Report] --> [Backend: Learner Profile Store]
```

## Core Interfaces & Contracts (see `instructions/Contract.md` for authoritative schemas)
- `UploadRequest` / `TopicRequest` → Backend Ingestion API
- `ParsedDocument` (RAG output: chunks + metadata + embeddings ref)
- `LearnerProfile` (level, language, time_budget_min, style, history)
- `LessonPlan` (ordered list of `LessonNode`: concept, depth, examples, visual_type, est_minutes)
- `TeachingSegment` (script text, visual_spec, language, avatar_cue)
- `RenderedVideoSegment` (video_url/path, duration, captions)
- `InteractionEvent` (question, expected_concept, options?, difficulty)
- `StudentResponse` (raw_answer, response_type)
- `EvaluationResult` (correct: bool, misconception_tag?, confidence, feedback_text)
- `AdaptationDecision` (action: ALLOW|MODIFY|REGENERATE|HUMAN, target_node_id, reason)
- `AssessmentReport` (score, strong_areas[], weak_areas[], recommended_next[])

## Module Breakdown
- **frontend**: renders upload/topic form, lesson video player, interactive Q&A widgets,
  learner dashboard/progress, language & time/level selectors.
- **backend**: API gateway, auth, session/state store, orchestrates calls between modules,
  exposes REST + WebSocket (for interaction turns) endpoints, owns `LearnerProfile` persistence.
- **ml_core**: document parsing (PDF/DOCX/PPTX → text+structure), concept/entity extraction,
  answer evaluation NLP, misconception classification.
- **ai_agent_orchestration**: the multi-agent Teacher (Planner, Explainer, Questioner,
  Evaluator/Adaptation Controller) implemented as an LLM-driven state machine over `LessonPlan`.
- **rag**: chunking, embedding, vector store (indexing + hybrid retrieval: internal doc +
  optional web), citation/grounding, hallucination-mitigation prompt patterns.
- **avatar_voice**: multilingual TTS, AI avatar/talking-head video generation, on-screen visual
  synthesis (diagram/equation/code/image renderer), final video composition.
- **mlops**: model/service deployment, vector DB ops, inference routing, monitoring/logging,
  cost & latency tracking, CI for model configs.
- **testing**: cross-module E2E teaching-session simulation, RAG groundedness evaluation,
  multilingual QA, avatar/video QA, regression harness (`run_all_diagnostics`).

## Tech Stack (proposed — confirm/adjust in Contract.md before build)
- **Frontend**: React (Next.js) + Tailwind, WebSocket client for live interaction.
- **Backend**: Python (FastAPI) — async, WebSocket support, easiest to share types with ML/AI layers.
- **AI Orchestration**: LLM API (e.g. Claude/GPT-class) via an agent/graph framework
  (e.g. LangGraph-style explicit state machine) — NOT a single giant prompt.
- **RAG**: LlamaIndex or LangChain for chunking/retrieval + a vector DB (Chroma for local/hackathon,
  Qdrant/Pinecone if cloud is available).
- **ML Core**: HuggingFace models for classification/embeddings where a smaller task-specific
  model is more reliable/cheap than calling the big LLM.
- **Avatar/Voice**: pluggable adapter interface — start with an open-source or free-tier
  TTS + simple avatar/slide-video composition (e.g. TTS + slides+captions rendered with a
  video lib), designed so a paid avatar API (e.g. D-ID/HeyGen-class) can be swapped in later
  without touching other modules (see Contract: `AvatarAdapter`).
- **Storage**: Postgres (learner profiles, sessions) + object storage (uploaded docs, rendered
  videos) + vector DB (embeddings).
- **Comms protocol**: REST for CRUD/upload, WebSocket for the turn-by-turn interactive lesson.

## Architectural Constraints
- All cross-module calls go through the contracts in `instructions/Contract.md` — no module
  reaches into another module's internals.
- The Teacher Agent's state machine stages (Understand/Plan/Explain/Demonstrate/Question/
  Evaluate/Adapt/Continue) must be explicit and inspectable (loggable), not hidden inside one
  opaque LLM call — this is required to demonstrate genuine adaptive behavior for the rubric.
