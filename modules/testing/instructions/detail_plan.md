# detail_plan.md — testing

## Goal
Own the cross-module test harness and the "does this actually behave like an adaptive AI
teacher" evaluation — directly protects the highest-weighted rubric area.

## Deliverables
1. **E2E teaching-session simulator** (`tests/e2e/`): scripted fixture sessions that drive the
   full loop with a fake/mocked `StudentResponse` sequence, asserting:
   - a wrong answer produces a *different* re-explanation than the original (not a repeat),
   - a correct answer advances to the next node,
   - repeated wrong answers eventually trigger `REGENERATE` or `HUMAN`,
   - final `AssessmentReport` schema and content are sane (score in [0,100], non-empty
     weak/strong areas when applicable).
2. **RAG groundedness eval** (`tests/eval/`): fixture document + Q&A pairs; assert answers stay
   within retrieved-context bounds (see `rag` detail_plan).
3. **Multilingual QA** (`tests/eval/`): same lesson requested in ≥2 languages; assert
   `LessonPlan` structure is language-invariant while `TeachingSegment.script_text` /
   `language` differ, and mid-lesson language switch preserves `node_id`/progress.
4. **Avatar/video QA** (`tests/e2e/` or module-owned, referenced here): assert every rendered
   segment's visual asset type matches its planned `visual_type` (no generic fallback for a
   math/code node).
5. **Load/perf smoke** (`tests/smoke/`): basic timing assertions so demo doesn't stall
   (e.g. plan generation < N seconds with mocked LLM).
6. **Regression runner**: `scripts/run_all_diagnostics.py` wrapper that invokes all of the above
   in one command and produces a pass/fail summary for `docs/progress.md`.

## Fixtures
`tests/fixtures/` holds: 1 sample PDF (short textbook chapter), 1 sample DOCX, 1 sample PPTX,
a handful of topic strings across subjects (math/physics/biology/history/programming), and
canned right/wrong/partial student-answer scripts per subject.
