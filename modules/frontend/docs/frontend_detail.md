# Frontend Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `frontend`  
> **Repository Path**: `modules/frontend/`  
> **Primary Role**: Student Interactive UI, Video Presentation Classroom & Real-Time Adaptation Visualizer  
> **Status**: **SCAFFOLDED & CONTRACT-LOCKED** (Design system specified in `05_Design.md`)  
> **Key Contracts**: Contract §1 (`UploadRequest`), Contract §2 (`TopicRequest`), Contract §3 (`LearnerConstraints`), Contract §7 (`RenderedVideoSegment`), Contract §8 (`InteractionEvent`), Contract §9 (`StudentResponse`), Contract §11 (`AdaptationDecision`), Contract §12 (`AssessmentReport`), Contract §13 (`LearnerProfile`)

---

## 1. The Task (In Simple Language)

Imagine walking into a futuristic, interactive classroom desk:
1. **The Welcome Desk**: You place your textbook on the desk (or type what topic you want to learn), select your level (beginner, intermediate, advanced), choose your language (English, Hindi, or Hinglish), and pick your time budget (a quick 5-minute recap or a deep 60-minute dive).
2. **The Virtual Classroom (The 3-Panel Desk)**:
   - **Left Screen**: Shows your lesson outline and lets you switch languages mid-lesson if you want the teacher to explain a tricky point in Hindi.
   - **Center Screen**: Plays the high-definition lesson video showing the AI Teacher speaking, with synchronized subtitles and clear diagrams, math formulas, or code on the digital board. When the teacher asks a question, the video smoothly pauses and presents interactive answer buttons.
   - **Right Screen (The "AI Brain Glass")**: An inspectable live feed showing what the AI Teacher is thinking in real time: *"Student missed the core concept -> Adjusting explanation to use a bicycle analogy."*
3. **The Report Card & Roadmap**: Shows what you mastered, highlights what needs practice, and points to the next milestone on your learning journey.

The **`frontend`** module is this complete interactive student portal. It is built to be responsive, engaging, and modern, bringing the AI Teacher's intelligence directly into the hands of the learner.

---

## 2. Technical Details & Architecture

The frontend application is engineered as a modern Single-Page / Server-Rendered Web Application (built with Next.js / React and modular CSS design tokens):

### Core Architecture & State Management
- **WebSocket-Driven Lifecycle**:
  Unlike traditional static video websites, the student's lesson flow is entirely synchronized by a bidirectional WebSocket connection to the backend (`/sessions/{id}/live`). The server dictates when video segments start, when interaction cards appear, and when the lesson concludes.
- **Three-Panel Educational Workspace (`05_Design.md`)**:
  ```
  +-----------------------------------------------------------------------------------+
  | Shikshak AI — Virtual Classroom                                [Lang: Hindi (IN)] |
  +--------------------+----------------------------------------+---------------------+
  | LEFT PANEL (20%)   | CENTER PANEL (55%)                     | RIGHT PANEL (25%)   |
  |                    |                                        |                     |
  | [Curriculum Tree]  | [HTML5 1080p Video Player]             | [Live Agent State]  |
  | * Node 1: Intro    | - 16:9 Responsive Canvas               | [EXPLAINING NODE 2] |
  | > Node 2: Core     | - Custom Controls & Progress           |                     |
  | * Node 3: Quiz     | - WebVTT Word-Level Captions Track     | [Adaptation Feed]   |
  |                    |                                        | "Student confused   |
  | [Constraints Info] | --- CHECKPOINT EVENT TRIGGERED ---     |  mass with weight.  |
  | - Level: Beginner  | [Interactive Question Card]            |  MODIFY: Swapping   |
  | - Budget: 20 min   | [ ] Option A                           |  to moon gravity    |
  |                    | [x] Option B (Selected)                |  analogy."          |
  | [Change Settings]  | [ ] Option C                           |                     |
  | (Mid-lesson switch)| [ Submit Answer Button ]               | [Running Score: 85%]|
  +--------------------+----------------------------------------+---------------------+
  ```

- **Dynamic Interaction Card Renderer**:
  Dynamically mounts specialized input widgets based on `InteractionEvent.type`:
  - `mcq`: Accessible radio button cards with instant visual feedback upon evaluation.
  - `short_answer`: Multiline text field with character count and voice-input option.
  - `problem`: Monospace mathematical formula or code editor input.
  - `explain_in_own_words`: Guided self-explanation reflection box.
- **Non-Destructive Mid-Lesson Language Switch**:
  Allows the student to toggle between English, Hindi, and Hinglish on the fly. The UI sends a control frame over the WebSocket; the server preserves lesson progress and seamlessly delivers subsequent video segments in the newly selected language.
- **Accessibility & Caption Synchronization**:
  The HTML5 `<video>` player dynamically binds `captions_vtt_url` to an active `<track kind="subtitles">` element, guaranteeing captions are always legible and synchronized.

---

## 3. What is Implemented Till Now (Current Status)

| Subsystem | Specification & Status | Status |
|---|---|---|
| **Design Specifications** | Authoritative 3-panel UI layout and theme tokens specified in `05_Design.md`. | **Complete** |
| **Contract Integration** | Pydantic and JSON schemas defined in `instructions/Contract.md` (§1, §2, §3, §7, §8, §9, §11, §12, §13). | **Contract-Locked & Verified** |
| **Module Instructions** | `instructions/overview.md`, `instructions/detail_plan.md`, `instructions/contract.md` defining screen requirements and WebSocket control events. | **Complete** |
| **Directory Skeleton** | `src/` and `tests/` (`unit/`, `integration/`, `e2e/`) partitioned and prepared. | **Scaffolded** |
| **Component Architecture** | Component blueprints (`VideoPlayer`, `InteractionCard`, `AdaptationFeed`, `CurriculumTree`, `UploadDropzone`) ready for frontend sprint. | **Next Immediate Sprint** |

---

## 4. Full File Structure

```
modules/frontend/
├── docs/
│   └── frontend_detail.md                      # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Authoritative cross-module contract definitions
│   ├── detail_plan.md                          # Screen specifications and WebSocket event contracts
│   └── overview.md                             # High-level module mission statement
├── src/
│   ├── .gitkeep                                # Active source directory
│   ├── __init__.py                             # (Module marker)
│   ├── components/                             # (Target React/Next.js architecture)
│   │   ├── classroom/                          # 3-Panel Classroom Components
│   │   │   ├── AdaptationFeed.tsx              # Right-panel live audit log and AI thought stream
│   │   │   ├── CurriculumTree.tsx              # Left-panel lesson outline and node progress tracker
│   │   │   ├── InteractionCard.tsx             # Center-panel interactive quiz & answer widgets
│   │   │   └── VideoPlayer.tsx                 # Center-panel HTML5 video player with WebVTT captions
│   │   ├── dashboard/                          # Learner Dashboard Components
│   │   │   ├── ConceptMasteryGrid.tsx          # Strong and weak concepts visual breakdown
│   │   │   └── LearningPathTree.tsx            # Visual skill tree and historical timeline
│   │   ├── landing/                            # Landing & Configuration Components
│   │   │   ├── ConstraintForm.tsx              # Level, language, time budget, and style selectors
│   │   │   └── UploadDropzone.tsx              # Drag-and-drop document upload (PDF/DOCX/PPTX)
│   │   └── report/                             # Assessment Report Components
│   │       └── AssessmentSummaryCard.tsx       # Final score, areas for growth, and next steps
│   ├── hooks/                                  # (Target architecture)
│   │   ├── useSessionState.ts                  # Session storage and reconnect logic
│   │   └── useWebSocketLesson.ts               # Bidirectional WebSocket event listener and dispatcher
│   ├── styles/                                 # (Target architecture)
│   │   ├── classroom.css                       # Dark-mode educational classroom design system
│   │   └── globals.css                         # Typography, colors, and layout utilities
│   └── pages/                                  # (Target Next.js routing)
│       ├── _app.tsx                            # Root application wrapper
│       ├── dashboard.tsx                       # Permanent learner profile dashboard
│       ├── index.tsx                           # Landing page (Upload / Topic input)
│       └── lesson.tsx                          # Live 3-panel interactive lesson room
└── tests/
    ├── e2e/
    │   └── .gitkeep                            # Browser automation tests (Playwright)
    ├── integration/
    │   └── .gitkeep                            # WebSocket relay and mock stream integration tests
    └── unit/
        └── .gitkeep                            # Component rendering and event handler unit tests
```

---

## 5. Detailed File Logic (Planned & Authoritative Architecture)

### Target Components & Modules
- **`src/pages/index.tsx` & `src/components/landing/`**:
  - `UploadDropzone.tsx`: Handles drag-and-drop file uploads (`.pdf`, `.docx`, `.pptx`, `.txt`). Displays file name, size, and parsing progress indicator.
  - `ConstraintForm.tsx`: Renders difficulty buttons (`Beginner`, `Intermediate`, `Advanced`), language selector dropdown (`English`, `Hindi`, `Hinglish`), time budget presets (`5 min`, `20 min`, `60 min`, `Multi-day`), and pedagogical style selector (`Exam-focused`, `Concept-first`).
  - Submits `UploadRequest` or `TopicRequest` to the backend REST API, receives `session_id`, and routes to `/lesson`.
- **`src/components/classroom/VideoPlayer.tsx`**:
  - Renders custom HTML5 video canvas (1920x1080 aspect ratio).
  - Loads `RenderedVideoSegment.video_url` and attaches `captions_vtt_url` to the `<track>` element for real-time word-level captions.
  - Handles buffer/loading states gracefully with an animated banner: *"The AI Teacher is preparing your explanation..."*
- **`src/components/classroom/InteractionCard.tsx`**:
  - Automatically replaces or overlays the video player when an `InteractionEvent` arrives over the WebSocket.
  - Renders MCQ options or text areas. Upon submission, emits `StudentResponse` (Contract §9) containing `node_id`, `raw_answer`, and calculated `response_time_sec`.
- **`src/components/classroom/AdaptationFeed.tsx`**:
  - Right-panel live audit log stream.
  - Renders animated chips for agent state (`EXPLAINING`, `EVALUATING`, `ADAPTING`).
  - Renders cards for each `AdaptationDecision` (Contract §11), highlighting why the AI Teacher chose `ALLOW`, `MODIFY`, or `REGENERATE`.
- **`src/hooks/useWebSocketLesson.ts`**:
  - Encapsulates the WebSocket connection lifecycle. Auto-reconnects on drop, serializes outgoing `StudentResponse` frames, and updates internal React state on incoming `RenderedVideoSegment` or `InteractionEvent` frames.

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Student Lands on Portal]
          |
          v
[Fill Constraints & Upload Document / Type Topic]
          |
          v
Submits UploadRequest (Contract §1) / TopicRequest (Contract §2)
          |
          v
Receives session_id -> Navigates to /lesson room
          |
          v
[useWebSocketLesson connects to ws://backend/sessions/{id}/live]
          |
          +====================== LIVE LESSON SESSION =====================+
          |                                                                |
          | <-- WS Event: RenderedVideoSegment (Contract §7)              |
          |     - VideoPlayer mounts video_url                             |
          |     - Attaches captions_vtt_url                                |
          |     - Right panel displays: [EXPLAINING Node 1]                |
          |                                                                |
          | <-- WS Event: InteractionEvent (Contract §8)                   |
          |     - Video pauses                                             |
          |     - InteractionCard mounts MCQ / Short-answer widgets        |
          |     - Right panel displays: [AWAITING STUDENT RESPONSE]        |
          |                                                                |
          | --> WS Event: StudentResponse (Contract §9)                    |
          |     - Dispatches {node_id, raw_answer, response_time_sec}      |
          |     - Right panel displays: [EVALUATING ANSWER...]             |
          |                                                                |
          | <-- WS Event: AdaptationDecision (Contract §11)                |
          |     - Renders adaptation rationale card in right-panel feed    |
          |       e.g. "MODIFY: Clarifying concept with skateboard analogy"|
          |                                                                |
          | <-- WS Event: AssessmentReport (Contract §12)                  |
          |     - Mounts AssessmentSummaryCard                             |
          |     - Displays final score, strong/weak areas, recommendations |
          +================================================================+
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Outbound** | `backend` | **Contract §1** (`UploadRequest`) | Multipart HTTP POST containing document bytes and `LearnerConstraints`. |
| **Outbound** | `backend` | **Contract §2** (`TopicRequest`) | JSON HTTP POST containing topic string and `LearnerConstraints`. |
| **Inbound** | `backend` | **Contract §5** (`LessonPlan`) | Populates the left-panel curriculum tree with node concepts and visual types. |
| **Inbound** | `backend` (from `avatar_voice`) | **Contract §7** (`RenderedVideoSegment`) | Center video player receives video URL, duration, and WebVTT caption track. |
| **Inbound** | `backend` (from `ai_agent_orchestration`) | **Contract §8** (`InteractionEvent`) | Triggers interactive question card overlay in center panel. |
| **Outbound** | `backend` (to `ml_core`) | **Contract §9** (`StudentResponse`) | Emits student's answer string and timing metrics over WebSocket. |
| **Inbound** | `backend` (from `ai_agent_orchestration`) | **Contract §11** (`AdaptationDecision`) | Appends live reasoning cards (`ALLOW`, `MODIFY`, `REGENERATE`) into right-panel feed. |
| **Inbound** | `backend` | **Contract §12** (`AssessmentReport`) | Mounts end-of-lesson assessment report and next-step recommendations. |
| **Inbound** | `backend` | **Contract §13** (`LearnerProfile`) | Populates the learner dashboard with historical mastery charts. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`frontend`** is the student's physical window into the system:
- Captures inputs for **Understand & Plan**.
- Plays the generated video for **Explain & Demonstrate**.
- Renders the interactive cards for **Question**.
- Visualizes the live audit feed for **Evaluate, Adapt & Continue**, making the AI Teacher's thought process transparent and defensible to hackathon evaluators.

---

## 9. Critical Notes for Any LLM Agent Working on This Module

> [!IMPORTANT]
> **Strict Guardrails for LLM Agents:**
> 1. **Server-Sequenced Flow**: Never attempt to advance the lesson using client-side JavaScript timers. The lesson flow is strictly event-driven; wait for the backend WebSocket to push the next `RenderedVideoSegment` or `InteractionEvent`.
> 2. **Captions Must Always Render**: To satisfy accessibility and hackathon evaluation requirements, always ensure the `<track>` element is correctly populated from `captions_vtt_url`.
> 3. **Mid-Lesson Language Switch Invariant**: Switching languages must emit a `{ type: "control", action: "language_switch", language: "hi" }` frame over the WebSocket. Never reload the webpage or wipe state; the server will update constraints and push the next segment in the new language.
> 4. **Handling Rendering Latency**: Video synthesis can take several seconds. The UI must show an engaging loading skeleton or preview message rather than freezing or showing a broken player.
