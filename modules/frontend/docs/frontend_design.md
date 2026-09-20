# Frontend Design & Demo Architecture Blueprint: Shikshak AI

> **Target Audience**: Hackathon Evaluators, Judges, and Demo Presenters.  
> **Design Philosophy**: This document defines the **functional structure, page breakdown, component hierarchy, interactive controls, live states, and winning demo flow** for the Shikshak AI frontend. It focuses strictly on information architecture, UI elements, user interaction points, and backend WebSocket/REST wiring — intentionally omitting CSS styling tokens or color schemes.

---

## 1. Hackathon Demo Winning Strategy

To score maximum points in a live 3–5 minute hackathon judging presentation, the frontend must immediately deliver on three critical moments:
1. **The "Zero Friction" Start (30 seconds)**: The judge sees an immediate choice between uploading real educational notes (PDF/DOCX/PPTX) or typing any STEM topic with constraints (level, language, time budget), producing a structured curriculum in under 3 seconds.
2. **The "Live Multi-Modal Classroom" (2 minutes)**: The judge sees the AI Teacher speaking in Hindi/English with synchronized subtitles, a dynamic visual blackboard (equations, graphs, code), and an interactive checkpoint question where the student can answer and get instant evaluation.
3. **The "AI Brain Glass" / Inspection Proof (1 minute)**: A dedicated live telemetry panel shows the judge that this is **NOT a pre-rendered video** — it displays real-time RAG citation chunks, ML Core evaluation confidence, and the Adaptation Controller making live pedagogical decisions (`ALLOW`, `MODIFY`, `REGENERATE`).

---

## 2. Complete Page & Screen Breakdown

The frontend application consists of **4 primary views**:

```
+-----------------------------------------------------------------------------------+
|                              APPLICATION PAGE FLOW                                |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ 1. Launchpad / Landing Page ]                                                  |
|       ├── Mode A: Upload Document (PDF / DOCX / PPTX / TXT)                       |
|       └── Mode B: Topic Search & Constraints (Level, Language, Time)              |
|                               │                                                   |
|                               ▼                                                   |
|  [ 2. Lesson Plan Review & Customization Modal ]                                  |
|       ├── Concept Node Roadmap (Intro -> Core -> Quiz -> Application)             |
|       └── "Start Interactive Lesson" CTA                                         |
|                               │                                                   |
|                               ▼ (Connects WebSocket /ws/teach)                    |
|  [ 3. Live 3-Panel Classroom (The Demo Core) ]                                    |
|       ├── Top Nav: Status, Language Switcher, Audio Mute, Raise Hand, Exit       |
|       ├── Left Panel: Curriculum Progress Tracker & Node Checklist                |
|       ├── Center Panel: 1080p Visual Board + Talking Avatar PiP + Subtitle Bar   |
|       │    └── Floating Overlay: Interactive Checkpoint Quiz & Feedback Card      |
|       └── Right Panel: Live AI Brain Feed (RAG Citations, ML Confidence, Adapt)   |
|                               │                                                   |
|                               ▼ (Triggered on Session Completion)                 |
|  [ 4. Post-Lesson Mastery & Report Card ]                                         |
|       ├── Final Mastery Score (0-100%)                                            |
|       ├── Strong Concepts vs Weak Concepts Breakdown                              |
|       ├── Recommended Next Learning Steps                                         |
|       └── Download Study Notes & Return to Dashboard                              |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## 3. Screen-by-Screen Structural Specifications

### Screen 1: The Launchpad (Onboarding & Mode Selection)

#### Purpose
Allows the user/judge to initiate a personalized learning session within seconds using either their own notes or an open-ended topic.

#### Structural Wireframe & Component Elements
- **Global Header / Top Bar**:
  - Logo & Brand: `Shikshak AI — Autonomous Pedagogical Engine`
  - Demo Presets Dropdown (`Physics: Newton's Laws (English)`, `Biology: Photosynthesis (Hindi)`, `CS: Binary Search Trees (English)`) for instant 1-click demo loading.
  - Active Learner Profile Avatar / Switcher (`Learner: Sagnik`, `Level: Class 10`).

- **Hero Dual-Card Mode Selector**:
  - **Card 1: "Upload Study Material" (RAG Ingestion Mode)**:
    - Drag & drop file dropzone supporting `.pdf`, `.docx`, `.pptx`, `.txt`.
    - File upload progress indicator bar.
    - Post-upload extraction summary card:
      - Document title and total pages/slides.
      - Detected chapters badge list (e.g., `["अध्याय 1: विद्युत", "Chapter 2: Resistance"]`).
      - Detected language badge (`Hindi`, `English`, `Bilingual`).
  - **Card 2: "Explore Any Topic" (Topic-Based Mode)**:
    - Topic search input field with placeholder: *"What do you want to master today? (e.g., Quantum Entanglement, Thermodynamics, Python Recursion)"*.
    - Quick-suggest pill tags: `Newton's Laws`, `Electromagnetism`, `Cell Division`, `Calculus Derivatives`.

- **Learner Constraints Configuration Bar**:
  - **Target Level Radio Pills**: `Beginner (Foundations)` | `Intermediate (Concept & Math)` | `Advanced (Exam & Deep Theory)`.
  - **Instruction Language Dropdown**: `English` | `Hindi (हिंदी)` | `Bengali (বাংলা)` | `Hinglish`.
  - **Time Budget Selector**: `5 min (Quick Recap)` | `15 min (Standard Lesson)` | `30 min (Masterclass)` | `Multi-Day Plan`.
  - **Teaching Style Preference**: `Visual & Intuitive` | `Exam-Oriented` | `Code & Problem Solving` | `Story-Driven`.

- **Primary Action Button**:
  - `[ Generate Personalized Lesson Plan ]` (Triggers `POST /api/v1/plan` or `POST /api/v1/topic`).
  - Spinner/Skeleton state showing: *"Analyzing material -> Structuring cognitive checkpoints -> Ready"*.

---

### Screen 2: Lesson Plan Review & Customization Modal

#### Purpose
Shows the judge that the AI does **not** jump into an unstructured monologue; it constructs a formal cognitive sequence with clear checkpoint milestones.

#### Structural Wireframe & Component Elements
- **Modal Header**:
  - Lesson Title (e.g., *"Kinematics: Velocity, Acceleration & Trajectory"*).
  - Source Badge: `Grounded on Uploaded PDF` or `Topic Exploration`.
  - Estimated Total Duration: `15 mins` | `3 Checkpoint Quizzes`.

- **Concept Node Roadmap (Linear Timeline)**:
  - List of sequentially ordered lesson nodes:
    - **Node 1**: Title (e.g., *"Foundational Principles"*), Depth: `intro`, Est. Duration: `3 min`, Visual Type: `diagram`, Checkpoint: `None`.
    - **Node 2**: Title (e.g., *"Equations of Motion"*), Depth: `core`, Est. Duration: `7 min`, Visual Type: `equation`, Checkpoint: `1 MCQ Quiz`.
    - **Node 3**: Title (e.g., *"Real-World Trajectory Problems"*), Depth: `advanced`, Est. Duration: `5 min`, Visual Type: `simulation`, Checkpoint: `1 Problem Solving`.

- **Action Controls**:
  - `[ Customize Topics ]` (Allows reordering or deleting non-essential nodes).
  - `[ Start Interactive Lesson ]` (Creates session via `POST /api/v1/session`, obtains token, connects to `/ws/teach`).

---

### Screen 3: The Live 3-Panel Classroom (The Demo Core)

#### Purpose
This is the primary demo screen where the video presentation, real-time avatar speech, visual board, interactive student questioning, and AI pedagogical adaptation happen simultaneously.

```
+---------------------------------------------------------------------------------------------------------+
| [LOGO] Shikshak AI | Topic: Newton's Laws | Concept: Inertia | [● Live Connected] | [EN|HI|BN] | [Hand] | [Exit] |
+-------------------------------+-----------------------------------------+-------------------------------+
| LEFT PANEL (20%): CURRICULUM  | CENTER PANEL (55%): CLASSROOM STAGE     | RIGHT PANEL (25%): AI BRAIN   |
|                               |                                         |                               |
| [Current Progress: 35%]       | +-------------------------------------+ | [ Tabs: AI Inspector | Notes ]|
|                               | | 16:9 VISUAL BLACKBOARD              | |                               |
| Concept Nodes:                | |                                     | | [CURRENT STATE: EVALUATING]   |
| [✓] 1. Intro to Force (3m)    | |  F = m * a                          | | - Active Node: node_2_core    |
| [▶] 2. Inertia & Mass (5m)    | |  [Dynamic LaTeX / Graph / Code]     | | - Target: Newton's 1st Law    |
| [ ] 3. Checkpoint Quiz        | |                                     | |                               |
| [ ] 4. Momentum Formula (7m)  | |                   +---------------+ | | [RAG CITATION GROUNDING]      |
|                               | |                   | AVATAR PiP    | | | Source: NCERT_Physics_Ch3.pdf|
| Student Settings:             | |                   | [Talking 24fps| | | Page 42, Chunk #10            |
| - Level: Intermediate         | |                   |  Viseme Mouth]| | "...an object remains in a    |
| - Audio: Swara (Neural Hindi) | |                   +---------------+ | | state of rest unless acted..."|
|                               | +-------------------------------------+ |                               |
| Controls:                     | | [SUBTITLES]: "Let's examine how     | | [ML EVALUATION RESULT]        |
| [ Repeat Last Concept ]       | |  inertia resists acceleration..."   | | - Score: 0.85 (Partial Credit)|
| [ Switch to Simpler Analogy ] | +-------------------------------------+ | - Misconception: Mass != Wt   |
|                               | | ▶ Play | ⏪ 10s | ⏩ 10s | 👍 Helpful| |                               |
|                               | +-------------------------------------+ | [ADAPTATION DECISION]         |
|                               |                                         | Action: MODIFY                |
|                               | --- WHEN QUIZ TRIGGERS (OVERLAY CARD) - | "Injecting lunar gravity      |
|                               | [ Checkpoint Question: Node 2 ]         |  analogy before proceeding."  |
|                               | "Why does a passenger jerk backward?"   |                               |
|                               | ( ) Option A: Gravity increases         | [LEARNER PERFORMANCE GAUGE]   |
|                               | (•) Option B: Inertia of rest [Selected]| Mastery: 82% | 2/2 Correct    |
|                               | [ Submit Answer ] [ 🎤 Voice Input ]    |                               |
+-------------------------------+-----------------------------------------+-------------------------------+
```

#### Detailed Element Breakdown for Screen 3

#### 1. Top Navigation Bar
- **Branding & Active Context**:
  - Shikshak AI Logo + Current Lesson Title + Active Concept breadcrumb.
- **WebSocket Status Indicator**:
  - Pulse Dot: Green (`Connected - Low Latency`) / Amber (`Reconnecting...`) / Red (`Offline`).
- **Live Language Switcher**:
  - Segmented toggle: `[ EN | हिंदी | বাংলা ]`.
  - When clicked, sends a control message over WebSocket; subsequent teacher video/audio segments switch language dynamically without restarting the lesson.
- **Audio & Playback Controls**:
  - Audio Mute / Unmute toggle button.
  - Speed selector: `[ 0.75x | 1.0x | 1.25x ]`.
- **Engagement & Emergency Buttons**:
  - **"Raise Hand / I'm Confused" Button**: Instantly emits a student struggle event to the backend, prompting the `AdaptationController` to trigger a `MODIFY` step (simpler explanation / bicycle analogy).
  - **"Exit Lesson" Button**: Safely disconnects WebSocket, finalizes assessment, and navigates to the Report Card.

#### 2. Left Panel: Curriculum Roadmap & Progress
- **Overall Lesson Progress Bar**: Shows percentage completion (e.g., `45% completed | 8 mins remaining`).
- **Node Progression Tree**:
  - Node card states:
    - `Completed`: Green checkmark, clickable to replay explanation.
    - `Active / Speaking`: Glowing highlight, animated speaker icon, concept title, depth pill (`core`).
    - `Upcoming / Locked`: Dimmed card with lock icon and time estimate.
- **Quick Assistance Shortcuts**:
  - `[ Repeat Concept ]`: Tells teacher to re-explain current slide.
  - `[ Give Me an Example ]`: Requests a real-life application visual.

#### 3. Center Panel: Classroom Visual Board & Video Stage
- **16:9 Presentation Canvas**:
  - **Visual Board (70% viewport)**:
    - Renders math equations (LaTeX), animated graphs, multi-step derivations with cyan/amber line reveals, or code execution output.
  - **Teacher Avatar PiP Window (30% bottom-right overlay)**:
    - 24 FPS animated avatar with synchronized lip movements (visemes), natural eye blinks, and emotional gestures matching cues (`emphasis`, `questioning`, `neutral`).
  - **Synchronized Subtitle Bar**:
    - Bottom captions with word-level highlighting matching Edge-TTS speech timing.
- **Player Action Bar (Directly beneath video)**:
  - Standard playback controls: Play/Pause, Rewind 10s, Fast Forward 10s.
  - Interactive Reactions:
    - `👍 Helpful` (Like reaction: logs positive feedback to session telemetry).
    - `💡 Ah, I get it now!` (Signals concept comprehension).
    - `❓ Still unclear` (Triggers visual re-render).

#### 4. Center Panel Overlay: Interactive Checkpoint Card
- **Trigger**: Automatically mounts when `TeacherState.INTERACT` arrives via WebSocket.
- **Content Elements**:
  - Question Header: Badge showing `Checkpoint Question` + concept node name.
  - Question Text: Clear, formatted question prompt.
  - **Dynamic Input Types**:
    - *For MCQ*: Radio button cards with option text. Immediate visual feedback upon selection.
    - *For Short Answer / Freeform*: Multiline text box + `[ 🎤 Speak Answer ]` microphone button (Speech-to-Text).
    - *For Math / Calculation*: Numeric input with unit dropdown (e.g., `m/s^2`).
  - `[ Submit Answer ]` Button: Dispatches `StudentResponse` over WebSocket.
- **Evaluation Feedback Banner (Post-Submission)**:
  - Pops up immediately after `EvaluationResult` is received:
    - Correct: Green banner with praise and confidence score.
    - Partially Correct: Amber banner showing partial credit (e.g., `+0.5`) and explanation.
    - Misconception Detected: Red/Orange card highlighting the exact false assumption (e.g., *"You equated mass with weight — remember mass is constant regardless of gravity."*).
  - `[ Continue to Next Concept ]` Button.

#### 5. Right Panel: "The AI Brain Glass" (Judge Inspection Feed)
- **Tab 1: AI Inspector (The Live Telemetry Stream)**:
  - **Current FSM State Pill**: Displays live state: `PLAN` ➔ `TEACH` ➔ `INTERACT` ➔ `EVALUATE` ➔ `ADAPT`.
  - **RAG Grounding Card**:
    - Displays the exact file name and page number currently cited.
    - Expandable snippet showing the exact textbook text grounding the teacher's current explanation.
  - **ML Core Evaluation Metrics**:
    - Confidence meter (e.g., `Confidence: 94%`).
    - Semantic match score vs. expected concept.
    - Active misconception tag (or `None`).
  - **Adaptation Decision Card**:
    - Action badge: `ALLOW` (Green), `MODIFY` (Amber), `REGENERATE` (Blue), `HUMAN_ESCALATION` (Red).
    - Pedagogical rationale string (e.g., *"Student answered correctly with high confidence. Pacing accelerated to Advanced node."*).
- **Tab 2: Lesson Notes & Key Formulas**:
  - Live scratchpad that automatically captures key formulas, definitions, and diagrams as the teacher introduces them.
  - `[ Copy Notes ]` and `[ Save as PDF ]` action buttons.

---

### Screen 4: Post-Lesson Mastery & Report Card

#### Purpose
Provides the student and evaluator with tangible evidence of learning gain, personalized remediation, and persistent learner profiling.

#### Structural Wireframe & Component Elements
- **Mastery Summary Header**:
  - Circular progress score (e.g., `85% Mastery Achieved`).
  - Lesson Title, total time spent, and questions answered.
- **Concept Breakdown Grid**:
  - **Strong Concepts (Green Pills)**: Concepts where the student scored 100% on first attempt (e.g., `Newton's First Law`, `Inertia of Rest`).
  - **Areas for Practice (Amber Pills)**: Concepts where misconceptions or retries occurred (e.g., `Action-Reaction Force Pairs`).
- **AI Teacher's Narrative Feedback**:
  - Humanized pedagogical summary paragraph generated by `AssessmentAgent`.
- **Recommended Next Milestones**:
  - 2–3 actionable cards for subsequent learning:
    - Card 1: `Practice 3 Numerical Problems on Momentum` [Start Quiz].
    - Card 2: `Advanced Concept: Elastic vs Inelastic Collisions` [Start 10m Lesson].
- **Action Buttons**:
  - `[ Download Study Report & Cheat Sheet (PDF) ]`
  - `[ Retake Tricky Questions ]`
  - `[ Return to Dashboard ]`

---

### Screen 5: Learner Profile & History Dashboard

#### Purpose
Demonstrates the backend's persistent `LearnerProfile` capabilities across sessions.

#### Structural Wireframe & Component Elements
- **Learner Stats Bar**:
  - Total Sessions Completed (e.g., `12 Lessons`).
  - Total Study Minutes (e.g., `145 mins`).
  - Overall Knowledge Score (e.g., `Level: Intermediate Scholar`).
- **Concept Knowledge Graph / Skill Tree**:
  - Interactive visual tags grouped by subject (`Physics`, `Mathematics`, `Computer Science`).
- **Recent Lesson History Table**:
  - Columns: `Date`, `Topic`, `Language`, `Score`, `Status`, `Action (Review Report / Replay)`.

---

## 4. Complete Component Hierarchy

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── TopNavbar.tsx               # Branding, live status, language switcher, audio controls
│   │   ├── ThreePanelLayout.tsx        # Responsive 20/55/25 grid container
│   │   └── FooterBar.tsx               # Session diagnostics & metadata
│   ├── launchpad/
│   │   ├── UploadDropzone.tsx          # Drag & drop document uploader (PDF/DOCX/PPTX)
│   │   ├── TopicSearchBar.tsx          # Topic input with quick-suggest chips
│   │   ├── ConstraintsSelector.tsx     # Level, language, time budget, style selectors
│   │   └── LessonPlanModal.tsx         # Pre-lesson curriculum roadmap preview
│   ├── classroom/
│   │   ├── CurriculumOutline.tsx       # Left-panel node checklist & progress timer
│   │   ├── VideoStage.tsx              # Center-panel 16:9 canvas container
│   │   │   ├── VisualBoard.tsx         # Math (LaTeX), graphs, code, diagrams renderer
│   │   │   ├── AvatarPiP.tsx           # 24 FPS animated viseme teacher overlay
│   │   │   └── SubtitleBar.tsx         # Synchronized word-by-word caption track
│   │   ├── PlayerControls.tsx          # Play/pause, replay concept, like/reaction buttons
│   │   └── InteractionOverlay.tsx      # Checkpoint quiz modal (MCQ, freeform, voice input)
│   │       ├── MCQWidget.tsx           # Radio cards with instant feedback
│   │       ├── VoiceTextInput.tsx      # Speech-to-text input with microphone button
│   │       └── EvaluationBanner.tsx    # Score, partial credit, and misconception tags
│   ├── telemetry/
│   │   ├── AIBrainFeed.tsx             # Right-panel live FSM state & adaptation log
│   │   ├── RAGCitationCard.tsx         # Grounding chunk preview & source document links
│   │   ├── AdaptationBadge.tsx         # ALLOW / MODIFY / REGENERATE decision visualizer
│   │   └── LessonNotesScratchpad.tsx   # Auto-accumulating formula & concept summary
│   └── report/
│       ├── MasteryScoreRing.tsx        # Circular percentage mastery indicator
│       ├── ConceptPillsGrid.tsx        # Strong vs weak concepts breakdown
│       └── RecommendedNextList.tsx     # Clickable follow-up learning milestones
├── hooks/
│   ├── useWebSocketLesson.ts           # Connects to /ws/teach, handles events & reconnection
│   ├── useAudioPlayer.ts               # Controls TTS audio playback and WebVTT timing
│   └── useLearnerSession.ts            # Manages session tokens, profile, and local checkpoints
└── pages/
    ├── index.tsx                       # Launchpad & topic/document onboarding
    ├── lesson.tsx                      # Live 3-panel classroom
    ├── report.tsx                      # Post-lesson assessment summary
    └── dashboard.tsx                   # Learner profile & historical skill tree
```

---

## 5. Live WebSocket Event-to-UI Action Mapping

| Backend Event (from `/ws/teach`) | Frontend Action / UI State Transition |
| :--- | :--- |
| `TEACH` (payload contains `TeachingSegment`) | • Left Panel: Updates active node to "Speaking".<br>• Center Stage: Renders `visual_spec` (equation/graph/code) on blackboard.<br>• Center Stage: Starts Avatar speech with viseme mouth animation.<br>• Subtitle Bar: Streams word-highlighted WebVTT captions.<br>• Right Panel: Logs FSM state `TEACH` + displays active RAG citation chunk. |
| `INTERACT` (payload contains `InteractionEvent`) | • Center Stage: Video pauses smoothly.<br>• Center Stage: Mounts `InteractionOverlay` with MCQ options or free-text box.<br>• Top Bar: Shows pulse reminder: *"Checkpoint Question Active"*.<br>• Right Panel: Logs FSM state `INTERACT`. |
| Student submits answer | • UI dispatches `StudentResponse` over WebSocket.<br>• Center Stage: Shows subtle analyzing spinner on button. |
| `EVALUATE` (payload contains `EvaluationResult`) | • Center Stage: Displays `EvaluationBanner` with green/amber/red status, partial credit, and misconception explanation.<br>• Right Panel: Updates ML Core confidence score and misconception tag. |
| `ADAPT` (payload contains `AdaptationDecision`) | • Right Panel: Highlights decision badge (`ALLOW`, `MODIFY`, or `REGENERATE`).<br>• If `MODIFY`: Banner notifies student: *"Adjusting next explanation with a simpler real-world analogy."*<br>• Next `TEACH` segment loads seamlessly. |
| `ASSESS` (payload contains `AssessmentReport`) | • Classroom disconnects cleanly.<br>• Smooth transition to Screen 4: Post-Lesson Mastery & Report Card. |

---

## 6. Recommended 3-Minute Live Demo Script for Presenters

1. **0:00 – 0:30 (The Hook & Input)**:
   - *"Welcome to Shikshak AI. Here we have a Class 10 NCERT Science PDF in Hindi. We drag it into the Launchpad, select 'Hindi', and click 'Generate Lesson Plan'. Within 2 seconds, the system parses the chapters, builds token budgets, and produces an adaptive curriculum."*
2. **0:30 – 1:30 (The Live Multi-Modal Teacher)**:
   - *"Now we enter the classroom. The AI Teacher begins speaking in fluent Hindi. Look at the digital blackboard: as the teacher speaks about Ohm's Law, the LaTeX formula and circuit diagram reveal progressively. Notice the bottom subtitles and the 24 FPS lip-synchronized avatar."*
3. **1:30 – 2:30 (The Interactive Checkpoint & Misconception Handling)**:
   - *"The teacher pauses to check our understanding. A checkpoint question pops up. We deliberately select a common misconception answer. Watch what happens: the ML Core catches the misconception, awards partial credit, and in the right panel, you see the Adaptation Controller trigger 'MODIFY'. The teacher immediately pivots to explain with a water-pipe analogy."*
4. **2:30 – 3:00 (The Assessment Report & Persistence)**:
   - *"At the end of the session, the student receives this comprehensive mastery report card showing strong areas, concepts to review, and recommended next steps. All results persist to the student's learning profile."*
