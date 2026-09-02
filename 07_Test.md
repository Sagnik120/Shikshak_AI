# 07_Test.md — Testing & Diagnostics Protocol

## Principle
1:1 mirror between `modules/<name>/src/` (once code exists) and `modules/<name>/tests/`.
Every module also gets tested from the ROOT `/tests/` folder for cross-module concerns.

## Per-Component Test Contract (minimum 5 cases per unit)
1. Clean/expected input.
2. Obvious-flag input (e.g. clearly wrong answer, clearly unsupported language).
3. Borderline input (e.g. ambiguous partial-credit answer, time budget of 0/negative).
4. Edge/malformed input (corrupt PDF, empty topic string, unsupported file type).
5. Cross-module interaction (e.g. RAG retrieval feeding Planner; Evaluator feeding Adaptation Controller).

## System Diagnostics & Smoke Tests
- `run_all_diagnostics.py` (root `/tests/`) must exercise the full pipeline end-to-end using a
  small fixture document + fixture topic, asserting: ingestion → lesson plan → teaching segment
  → mock video render → interaction → evaluation → adaptation → assessment report — all produce
  schema-valid outputs per `instructions/Contract.md`.
- Must run in CI on every PR; zero tolerance for regressions in previously-passing checks.

## Root `/tests/` Hierarchy
```
tests/
  unit/            # cross-module pure-function tests (schema validators etc.)
  integration/     # 2-module contract tests (e.g. rag -> ai_agent_orchestration)
  e2e/             # full teaching-session simulation(s)
  eval/            # RAG groundedness eval, multilingual QA, misconception-detection accuracy
  smoke/           # fast pre-commit sanity checks
  fixtures/        # sample PDFs/DOCX/PPTX, sample topics, sample student answer scripts
```
