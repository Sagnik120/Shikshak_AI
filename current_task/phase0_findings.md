# Phase 0 — Baseline & Contract Audit (read-only findings)

Confirms or corrects every *(inference)* item in §2/§4 of `task_agentic_ai_modernization.md`.

## Corrections to the plan

| Plan claim | Reality in code |
|---|---|
| §2.5 `mlops` has a PerfTrace Instrumentor + Telemetry/Benchmark Logger | **Wrong.** `modules/mlops/src/` is empty (`.gitkeep` only). The only perf code is `modules/rag/src/perf.py` (`@timed` + `PerfTrace`, RAG stages only). `mlops/instructions/detail_plan.md` §3 does assign "structured logs for every agent-stage transition" to this module → correct home for Phase 1, but it must be **built**, not extended. |
| §2.4 `learner_profiles` contents unconfirmed | **Already fully implemented.** `LearnerProfileRow` has `strong_concepts`, `weak_concepts`, `current_learning_path`, `misconception_counts` + lesson/question/streak stats. `lesson_service.refresh_learner_profile()` recomputes it from every lesson; called on completion, escalation, dashboard load and lesson delete. **Phase 5's write side already exists** — do not rebuild it. |
| §4.5 needs a new `agent_events` table | **Not needed.** `lesson_events` is already `{event_type, lesson_id, node_id, payload JSON, occurred_at}` — exactly the shape §4.5.D specifies, and `lesson.id` *is* the orchestrator `session_id` (verified in a live server log). Reuse it; only 7 lifecycle writes exist today and there is **no read path/API**. |
| §4.3 "citation threshold ≈0.52 *(inference)*" | **Confirmed exactly.** `retrieval/retriever.py`: `top_score >= 0.52` → sufficient/`low`; `0.5001 < top < 0.52` → sufficient/`moderate_relevance`; `<= 0.5001` or no chunks → insufficient/`high_hallucination_risk`. Phase 3 reuses `has_sufficient_context`/`risk_level` — **no new threshold is introduced.** |
| §2.2 FSM is hand-rolled | Confirmed. `TeacherOrchestrator.step()` dispatches on `TeacherState`; `logging_utils.log_transition()` already emits structured transition dicts into `SessionState.state_logs`. |

## Phase 5's actual gap (smaller than the plan assumed)
`PlannerAgent.plan_lesson()` already accepts a `learner_profile` argument and injects it into the
prompt payload — but **the orchestrator never passes one**, and `planner_system.md` never mentions
`learner_profile`, so the model gets no instruction for it. The wiring is dead on both ends.
Phase 5 = connect those two ends + prompt guidance. No new storage, no schema change.

## Contract impact
**None.** `RetrievalResult`/`RetrievedChunk` are RAG-internal (absent from `Contract.md`), so Phase 3's
additions are additive-optional. `LearnerProfile` (§13) already declares `strong_concepts`/
`weak_concepts`/`current_learning_path`. No contract change is requested.

## Scope decision (per the plan's own §8 Priority Matrix)
- **Implementing:** Phase 1 (Must), Phase 3 (Must), Phase 5 (Should), Phase 6 (integration).
- **Deferring Phase 2 (LangGraph)** — §8 ranks it "Could Have" and states it "can be deferred without
  blocking Phases 3/5". It adds a heavyweight dependency to a <512 MB free-tier deploy and is the
  highest-risk touch to working core orchestration. Phases 3/5 are implemented as plain bounded
  Python, exactly as §8 permits.
- **Deferring Phase 4 (MCP)** — §8 lists it under "Future Scope"; it adds a process/IPC boundary on
  the same constrained deploy for no correctness gain over Phase 3's direct calls.

## Phase 3 design note (avoids a cost the plan assumed)
§4.3.D suggests an LLM call to refine the query. Not needed: refinement is **deterministic**
(concept + topic + document key terms, stopwords dropped), so the loop adds **no Gemini round-trip,
no quota use**, and is fully offline-testable. Risk §4.3.G (latency/quota) is designed out.
