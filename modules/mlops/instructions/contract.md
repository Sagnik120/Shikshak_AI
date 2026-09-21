# contract.md — mlops (module-local pointer)

This module implements/consumes the schemas defined in the ROOT `instructions/Contract.md`.
Do not redefine schemas here — only note any mlops-specific internal (non-cross-module) types.

## Module-internal types (not part of the cross-module contract)
- `AgentEvent` (`src/agent_trace.py`) — one agent decision, as written to the existing
  `lesson_events` table by the backend sink:
  `{event_type, session_id, node_id, occurred_at, payload}`.
  `session_id` is the lesson id. `payload` holds **observable metadata only** — chunk ids and
  scores, decision + reason code, counts. Prompts, scripts, raw answers, reasoning and
  credentials are stripped by `_SENSITIVE_KEYS` before the event leaves the process, so a trace
  is safe to show a learner or a judge.
  Event types: `agent.plan_generated`, `agent.retrieval_attempt`, `agent.retrieval_resolved`,
  `agent.segment_generated`, `agent.question_generated`, `agent.answer_evaluated`,
  `agent.adaptation_decided`, `agent.memory_read`.
  Producers (`ai_agent_orchestration`, `rag`) call `tracer.emit(...)` and never import the
  backend; the backend installs the persistence sink at startup. Read back via
  `GET /api/v1/lessons/{id}/trace`.
