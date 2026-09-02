# detail_plan.md — frontend

## Goal
Deliver the full student-facing journey: input constraints → watch AI-teaching video →
answer in-lesson questions → see live adaptation state → get final report → view learner dashboard.

## Concrete Screens
1. **Landing/New Session** — upload dropzone (PDF/DOCX/PPTX/TXT) OR topic text field; constraint
   form (level select, language select/free-text, time budget presets [5/20/60 min / 7-day plan],
   style optional field). Submits `UploadRequest`/`TopicRequest` per Contract.
2. **Lesson Room** (3-panel layout per `05_Design.md`):
   - Left: constraints summary + "change settings" (allows mid-lesson language switch).
   - Center: video player for current `RenderedVideoSegment`; on checkpoint, swaps to an
     Interaction Card rendering the current `InteractionEvent` (MCQ buttons / short-answer box /
     problem input); submits `StudentResponse` over WebSocket.
   - Right: live agent-state chip + `AdaptationDecision` feed (audit log) + running score.
3. **Assessment Screen** — final quiz flow (batched `InteractionEvent`s), submit all, show
   `AssessmentReport` (score, strong/weak areas, recommendation) styled per PS §13 example.
4. **Learner Dashboard** — `LearnerProfile` view: history, strong/weak concepts, current
   learning path (visual path/tree per PS §15 example: Python Fundamentals → ... → Advanced ML).

## Real-time behavior
Use one WebSocket per session: server pushes `TeachingSegment`/`RenderedVideoSegment`/
`InteractionEvent`/`AdaptationDecision`; client pushes `StudentResponse` and
"language_switch"/"pause"/"resume" control events. Video playback and question-cards are
sequenced by the server-driven event stream, not client-side timers.

## Multilingual UI
Language switch mid-session sends a control event; UI must NOT reset lesson progress — only the
subsequent `TeachingSegment`s/`InteractionEvent`s change language (server preserves `lesson_id`
and current `node_id`).

## Non-functional
- Must gracefully handle slow video generation (loading state, "AI is preparing your lesson...").
- Accessible: captions always rendered for the video (from `captions_vtt_url`).

## Explicitly out of scope for MVP
Institutional login/SSO, payment, multi-tenant admin panel.
