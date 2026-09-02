# new_phases.md — Round 2 Feature Spec Roadmap

Legend: `[ ]` not started · `[~]` spec drafted · `[x]` coded and tested

## Batch A — Detection Layer
- `[ ]` Misconception classifier v2 (trained/few-shot over common wrong-answer patterns per
  subject) — ref: error-analysis / diagnostic-question literature (e.g. DKT-style diagnostic
  question banks).
- `[ ]` Confusion/struggle signal detection from response latency + hedging language in
  free-text answers.
- `[ ]` Language-mismatch detector (uploaded doc language vs requested teaching language).

## Batch B — Decision Logic Layer
- `[ ]` Adaptation Controller v2: replace heuristic ALLOW/MODIFY/REGENERATE/HUMAN thresholds
  with a learned/prompted policy conditioned on rolling `EvaluationResult` history (mirrors
  mastery-tracking approaches, e.g. Bayesian Knowledge Tracing / Deep Knowledge Tracing).
- `[ ]` Time-budget re-allocator: dynamically re-splits remaining lesson time across remaining
  `LessonNode`s when a re-explanation consumes more time than planned.

## Batch C — Advanced Features (PS §18)
- `[ ]` Real-time conversational teaching (streaming STT + incremental TTS).
- `[ ]` Multiple teacher personalities / avatar characters.
- `[ ]` Emotion-aware interaction (tone from text/voice sentiment).
- `[ ]` Long-term student memory across many sessions (spaced-repetition aware).
- `[ ]` Automatic study planner / exam-prep mode / revision mode.
- `[ ]` Flashcard generation & concept maps.
- `[ ]` Coding demonstration mode (live code execution + output visualization).
- `[ ]` Offline/local model fallback path.
- `[ ]` Accessibility features (captions, screen-reader friendly transcripts).

## Handoff Rule
Specs are handed to the coding agent **one at a time**, in order within a batch, following
`00B_SPEC_UPGRADES.md`.
