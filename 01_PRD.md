# 01_PRD.md — Product Requirements Document

## Project Name
**Shikshak AI** — "Shikshak" (शिक्षक) means "Teacher" in Hindi/Sanskrit.

## Product Name
**Shikshak AI** ("Shikshak" / शिक्षक = "Teacher") — a human-like AI educator that teaches through generated video, adapts to the
learner in real time, and grounds explanations in uploaded material via RAG.

## Source
Derived from: `Round 2 Technical Assessment.docx` — AI Innovation Hackathon 2026,
Challenge: "AI Teacher: Build a Human-Like AI Educator That Teaches Through Video."

## What We Are Building
A full-stack system where a student either (a) uploads learning material (PDF/DOCX/PPTX/notes/
research paper) or (b) names a topic, plus constraints (level, language, time budget, style).
The system:
1. Ingests & understands the material (RAG-grounded) or plans from world/topic knowledge.
2. Generates a structured, personalized lesson plan.
3. Produces an AI-teacher-presented video (avatar + voice + on-screen visuals: diagrams,
   equations, code, images) for the explanation portion.
4. Interactively questions the student mid-lesson (MCQ / short-answer / conceptual).
5. Evaluates responses, detects misconceptions, re-explains / adapts difficulty.
6. Runs a final assessment and produces a learning report + next-topic recommendation.
7. Persists a learner profile across sessions to personalize future lessons.

## Why This Exists
Existing platforms are either static video (no adaptation) or text chatbots (no teaching
structure, no video, no pedagogy). Neither replicates the **Understand → Plan → Explain →
Demonstrate → Question → Evaluate → Adapt → Continue** loop of a real teacher. Constraint:
this is a hackathon build — favor an architecture that lets a small team parallelize
(module-per-team-member) and reach a demoable, evaluable prototype within the timebox, while
still being technically defensible against the 100-point rubric.

## Core Capabilities & Allowed System Actions
Every teaching-loop step maps to one of:
- **ALLOW** — proceed to next stage automatically (e.g. student answered correctly → continue).
- **MODIFY** — adjust the existing lesson plan node (e.g. simplify explanation, swap analogy).
- **REGENERATE** — re-plan a lesson segment from scratch (e.g. student is fundamentally lost).
- **HUMAN** — surface to a human/UI decision point (e.g. ambiguous upload, unsupported language
  requested, safety-flagged content).

## Target Users
- Students (school/college/self-learners) uploading material or naming a topic.
- (Secondary) Educators wanting to preview/curate AI-generated lessons.

## Non-Goals (explicit, to prevent scope creep)
- NOT a general-purpose chatbot / open Q&A tool with no lesson structure.
- NOT a static pre-rendered video library.
- NOT a full LMS (grading integrations, institutional rostering) — learner profile is
  self-contained to this app.
- NOT real-time livestreaming avatar (turn-based interactive video is acceptable for MVP;
  true real-time conversation is an Advanced Feature, see `new_phases.md`).
- NOT guaranteeing zero hallucination — the goal is RAG-grounded minimization, with citations.

## Mandatory Requirements (must all be demoable — from PS section 17)
1. Learning from uploaded material (RAG).
2. Topic-based teaching (no upload).
3. AI-generated lesson structure.
4. Personalized teaching (level/style/language/time).
5. Human-like teaching interaction (full loop, not Q&A).
6. Video-based AI Teacher presentation.
7. AI voice (multilingual TTS).
8. Human-like AI avatar.
9. Multilingual capability.
10. Student questioning & assessment.
11. Adaptive response to student performance.
12. Working application/prototype.

## Evaluation Rubric (drives prioritization — PS section 19)
| Area | Weight |
|---|---|
| Human-Like Teaching & Adaptation | 20 |
| AI/ML & LLM Implementation | 15 |
| RAG & Knowledge Grounding | 15 |
| AI Teaching Video Generation | 15 |
| Multilingual Capability | 10 |
| Voice & AI Avatar | 10 |
| Innovation & Originality | 5 |
| UX/UI | 5 |
| Documentation | 5 |

**Implication for build order:** Teaching-loop/adaptation logic and RAG grounding are worth
more (35 pts combined) than avatar/video polish (25 pts) — do not over-invest in video fidelity
at the expense of the adaptive teaching state machine.
