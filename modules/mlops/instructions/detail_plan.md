# detail_plan.md — mlops

## Goal
Keep the AI-heavy pipeline (LLM calls, embeddings, TTS, avatar rendering) reliable, observable,
and cost/latency-aware during both development and the live demo.

## Responsibilities
1. **Service orchestration**: local dev docker-compose (backend, vector DB, any local model
   servers) so the whole system runs with one command for demo day.
2. **Model/service registry & adapters**: maintain the concrete implementations behind
   `LLMAdapter`/`TTSAdapter`/`AvatarAdapter`/`VectorStoreAdapter` (root Contract §14), with
   config-driven provider selection (env var picks provider, no code changes needed to swap).
3. **Monitoring/logging**: structured logs for every agent-stage transition (ties into the
   frontend audit-log panel and is essential for debugging adaptive-loop bugs); log latency and
   token/cost per LLM call.
4. **Caching**: cache embeddings for repeated documents; cache rendered video segments keyed by
   `(node_id, language, avatar_cue)` hash to avoid re-rendering identical segments during demo
   rehearsal.
5. **CI**: run `tests/smoke` + module unit tests on every PR; run `run_all_diagnostics.py`
   nightly or pre-demo.
6. **Resource/cost tracking**: simple per-session cost estimator (LLM tokens + TTS chars +
   avatar render count) surfaced in `docs/known_limitations.md`/architecture doc for judges.

## Explicitly out of scope for hackathon MVP
Multi-region deployment, autoscaling infra, full Kubernetes setup — a single deployable
demo instance (or docker-compose) is sufficient.
