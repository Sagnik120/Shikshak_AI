# detail_plan.md — ai_agent_orchestration

## Goal
Implement the actual "teacher" as an explicit multi-stage agent/state machine — this is the
highest-weighted rubric area (20 pts directly + heavily influences AI/ML 15 pts). Must NOT be a
single "answer this question" prompt.

## Agents (each a distinct, independently promptable/testable unit)
1. **Planner Agent** — input: `ParsedDocument` (optional) + `topic` (optional) +
   `LearnerConstraints` + `LearnerProfile` (for personalization from history) → output:
   `LessonPlan`. Must respect time budget (PS §7: 5 min = key concepts only; 20 min = structured
   w/ examples; 60 min = deep + questions + assessment; 7 days = multi-session revision plan —
   represent this as multiple `LessonPlan`s or a `LessonPlan` with `session` grouping).
2. **Explainer Agent** — input: one `LessonNode` (+ retrieved grounding chunks from `rag` if a
   document exists) → output: `TeachingSegment`. Must cite/ground claims when a source document
   exists (pass retrieved chunk ids through so `avatar_voice`/frontend can optionally show
   "based on Chapter 4, p.12").
3. **Questioner Agent** — input: `LessonNode` (where `checkpoint_question: true`) + recent
   teaching context → output: `InteractionEvent`. Vary question type (MCQ/short-answer/
   problem/application/"explain in your own words") — do not always ask MCQ.
4. **Adaptation Controller** — input: `EvaluationResult` (+ history of recent results for this
   session) → output: `AdaptationDecision`.
   - `correct` + high confidence → `ALLOW` (continue to next node).
   - `partial_credit` mid-range → `MODIFY` (re-explain same node with a different analogy/
     example, do not just repeat verbatim).
   - `incorrect` with identified `misconception_tag` → `MODIFY` targeting the misconception
     specifically (PS §12 example flow: identify → re-explain → new analogy → new example →
     re-question → re-evaluate).
   - repeated failure (≥2) on the same node → `REGENERATE` (re-plan that segment, possibly
     lowering depth) or `HUMAN` if still unresolved after regeneration.
5. **Assessment Agent** — input: full session's `EvaluationResult` history → output:
   `AssessmentReport` (score, strong/weak areas, recommendation) matching PS §13's example format.

## Orchestration pattern
Implement as an explicit finite-state machine (not a single chained prompt) so each transition
is loggable/inspectable — required for the rubric's "genuine AI-driven teaching capability"
evaluation focus, and directly powers the right-panel audit log in the frontend.

## Prompting guidance
- Use structured/JSON-mode outputs for every agent (matches Contract schemas exactly) —
  never free-text between agents.
- Explainer Agent prompt must explicitly forbid inventing facts not in the retrieved context
  when a source document exists (hallucination minimization, ties to `rag` module).
- Keep each agent's system prompt subject-agnostic; subject-specific behavior comes from the
  `visual_type`/context data, not hardcoded per-subject prompts (keeps it generalizable).
