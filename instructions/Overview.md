# Overview.md — Whole-System Overview (fast onboarding for any LLM/agent)

## One-paragraph summary
AI Teacher ingests either an uploaded document or a bare topic plus learner constraints
(level, language, time, style), plans a structured lesson (RAG-grounded when a document is
present), renders each lesson step as a short AI-avatar teaching video with subject-appropriate
visuals, pauses to ask the student questions, evaluates answers (including misconception
detection), adapts the remaining lesson accordingly, and ends with an assessment + learning
report that updates a persistent learner profile.

## The 8-stage teaching loop (must be explicit, not hidden in one LLM call)
`Understand → Plan → Explain → Demonstrate → Question → Evaluate → Adapt → Continue`
Each stage is owned by a specific module/agent (see `02_Architecture.md` Module Breakdown) and
each transition is a loggable event so the right-panel UI (see `05_Design.md`) can show live
"what is the AI teacher doing right now."

## Why this matters for the hackathon rubric
- 20 pts: the loop above, actually looping (not a scripted demo) = "Human-Like Teaching and Adaptation."
- 15 pts: `rag/` module's chunk+retrieve+cite pipeline = "RAG and Knowledge Grounding."
- 15 pts: `avatar_voice/` module's real video composition (avatar+voice+diagrams/equations/code,
  not just avatar-reads-text) = "AI Teaching Video Generation."
- 15 pts: `ai_agent_orchestration/` + `ml_core/` = "AI/ML and LLM Implementation."
- 10+10 pts: multilingual mid-lesson switching + voice/avatar quality.
- Remaining 15 pts: innovation, UX, docs — do last, after the loop works end-to-end.

## Golden rule for any agent picking up any module
Read your module's `instructions/overview.md` + `instructions/detail_plan.md` + root
`instructions/Contract.md` before writing a single function. If your planned function's
input/output doesn't match the Contract, fix the Contract first (propose in `06_Memory.md`),
don't silently diverge.
