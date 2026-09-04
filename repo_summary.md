# Repository Summary

## 1. Project Overview
**Shikshak AI** is a full-stack educational application being built for the AI Innovation Hackathon 2026. The goal is to build a human-like AI educator that teaches through generated video, grounds its explanations in uploaded material via RAG, and adaptively interacts with the learner in real-time. It moves beyond standard chatbots by structuring lessons, presenting them as an avatar, assessing understanding, and dynamically adjusting its teaching strategy based on student performance.

## 2. Current Architecture
The system follows a highly modular design built around clear data contracts:
```text
[Frontend (React)] <--> [Backend (FastAPI) API/WS]
                               |
             +-----------------+------------------+
             |                 |                  |
    [AI Orchestration]    [ML Core]             [RAG]
    (Agent State Machine) (Heuristics/NLP)  (Chroma/Chunking)
             |
    [Avatar & Voice] (TTS + Compositor)
```
**Key design constraint**: All cross-module calls strictly adhere to schemas defined in `instructions/Contract.md`. 

## 3. Current End-to-End Flow
**Intended Flow**:
1. User uploads document or topic.
2. **RAG/ML Core** parses and chunks material.
3. **AI Orchestration (Planner)** generates a lesson plan.
4. **Explainer Agent** generates a script.
5. **Avatar/Voice** renders the teaching video.
6. **Questioner Agent** pauses the lesson to ask questions.
7. **Answer Evaluator (ML Core)** assesses the student's answer.
8. **Adaptation Controller** decides next steps (ALLOW/MODIFY/REGENERATE).

**Actual Implemented Flow**:
Currently, the **RAG**, **Avatar/Voice**, **AI Agent Orchestration**, and **ML Core** pipelines are fully implemented and tested in isolation. The full end-to-end flow is not yet runnable because the Backend and Frontend modules are missing.

## 4. Repository Structure
- `modules/rag/`: Implemented. Contains document parsing, embedding generation, ChromaDB vector store adapter, and hybrid retrieval.
- `modules/avatar_voice/`: Implemented. Contains text-to-speech adapters, visual rendering, a Viseme avatar adapter, and an FFmpeg compositor.
- `modules/ai_agent_orchestration/`: **IMPLEMENTED**. Contains core FSM, teaching agents, and adaptation controller.
- `modules/ml_core/`: **IMPLEMENTED**. Contains evaluators, concept extraction, misconception classification, and visual rule mappings.
- `modules/backend/`: **MISSING** (only `.gitkeep` and planned instructions).
- `modules/frontend/`: **MISSING** (only `.gitkeep` and planned instructions).
- `docs/` & `*.md` files (root): Extensive PRDs, architectural constraints, and design specs.

## 5. AI Agent Orchestration
This is the core of the adaptive teaching engine, planned as a finite-state machine (not a single prompt).
- **Planner Agent**: Generates `LessonPlan` respecting time budget and learner profile.
- **Explainer Agent**: Generates `TeachingSegment` from a lesson node, grounded by RAG.
- **Questioner Agent**: Generates interactive questions mid-lesson.
- **Adaptation Controller**: Uses evaluation results to guide the state machine (ALLOW/MODIFY/REGENERATE).
- **Assessment Agent**: Produces the final learning report.

*Status: IMPLEMENTED. Code and offline unit/integration tests are complete.*

## 6. Adaptive Teaching / Teacher State
The system explicitly tracks the teaching loop via specific adaptation decisions:
- **ALLOW**: Student understood (correct answer). Continue to next node.
- **MODIFY**: Partial credit or identified misconception. Target the misconception and re-explain with a new analogy/example.
- **REGENERATE**: Repeated failures. Abandon current node and re-plan the segment.
- **HUMAN**: Unresolvable state requiring human fallback.
This logic resides in the Adaptation Controller, which is currently implemented and tested.

## 7. ML Core
The ML Core handles specific NLP tasks cheaper/more reliably than raw LLM calls.
- **Document Parser**: Extracts text + structure.
- **Concept Extractor**: Identifies key terms.
- **Answer Evaluator**: Classifies correct/partial/incorrect (MCQ rules + free-text LLM judge).
- **Misconception Classifier**: Few-shot classification to tag specific misunderstandings.
- **Visual-Type Suggester**: Recommends diagrams/equations based on subject rules.

*Status: IMPLEMENTED. Source and 20 offline tests are complete.*

## 8. RAG + Other Major Components
- **RAG (Implemented)**: Handles parsing (PDF/DOCX/PPTX), chunking, embedding generation (with factory patterns), and indexing using ChromaDB. Exposes a unified `RAGService`.
- **Avatar & Voice (Implemented)**: Enqueues and renders video segments asynchronously. Integrates TTS, visual generation, avatar viseme animation, and FFmpeg video compositing via `AvatarVoiceService`.

## 9. Current Status & Gaps

| Component | Status | Relevant Files | Main Gap |
|---|---|---|---|
| **RAG** | IMPLEMENTED | `modules/rag/src/service.py` | Integration with Planner/Explainer |
| **Avatar & Voice** | IMPLEMENTED | `modules/avatar_voice/src/service.py` | External API integrations (HeyGen/D-ID) |
| **AI Orchestration** | IMPLEMENTED | `modules/ai_agent_orchestration/src/` | Integration with real ML Core |
| **ML Core** | IMPLEMENTED | `modules/ml_core/src/` | Testing is complete; integration with Backend pending |
| **Backend API** | MISSING | `modules/backend/src/` | FastAPI server, websockets, state store |
| **Frontend App** | MISSING | `modules/frontend/src/` | React UI, video player, Q&A interaction |

## 10. Tests / Known Issues
- **Implemented**: RAG, Avatar/Voice, AI Orchestration (27 tests), and ML Core (20 tests) have isolated test suites. Total 47 passing tests for core teaching engines.
- **Missing**: Cross-module E2E teaching session simulations and regression tests are non-existent due to missing backend/frontend modules.
- **Risks**: The integration boundary between Backend/Frontend and the newly built Orchestration/ML engines remains untested.

## 11. Remaining Work
- **P0**: Build the `backend` FastAPI server to orchestrate requests.
- **[DONE]**: Implement the `ai_agent_orchestration` state machine (Planner, Explainer, Controller).
- **[DONE]**: Implement `ml_core` Answer Evaluator to support the teaching loop.
- **P0**: Build the `frontend` React UI (video player, interaction widgets).
- **P1**: Connect `frontend` to `backend` via WebSockets for real-time interaction.
- **P2**: Refine UI aesthetics, add advanced misconception tagging.

## 12. Developer Quick Start
- Review `instructions/Contract.md` for schemas.
- Examine `modules/ai_agent_orchestration/src/` and `modules/ml_core/src/` to understand the currently implemented agent workflows and evaluation mechanics.
- Next steps involve scaffolding the FastAPI backend in `modules/backend/src/`.

## 13. Critical Context
- **Contract Enforcement**: Cross-module communication must strictly adhere to the schemas defined in `instructions/Contract.md`. Do not bypass them.
- **Explicit State Machine**: The AI Orchestration must be built as an inspectable, loggable finite-state machine. Do not condense the teaching loop into a single giant LLM prompt; it will fail the hackathon rubric.
