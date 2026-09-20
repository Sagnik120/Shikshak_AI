# Agentic AI Modernization — Implementation Plan

> No live repo access. Based on supplied docs (`Contract.md`, `01_PRD`, `02_Architecture`, `04_Phases`, `08_Folder_Structure`, `Rules_Design_Test_Details`, `current_overall_status`, `repo_summary`, README, both architecture diagrams) and prior conversation context. CURRENT = evidenced by those materials. PROPOSED = new work this plan defines. FUTURE = explicitly deferred. Where evidence is thin, marked *(inference)* — implementation agent must confirm in code before acting on it.

## 1. Objective
Modernize Shikshak AI's agentic layer with five candidate technologies — LangGraph, MCP, Agentic RAG, Agent/Pedagogical Memory, Agent Evals+Tracing — validating each against the real architecture rather than adopting by default, and produce an incremental, contract-preserving, dependency-ordered phase plan.

## 2. Current Architecture Understanding

### 2.1 Existing System
FastAPI backend + Vanilla JS SPA (15 screens) + SQLite (WAL) via SQLAlchemy, deployed on a constrained free-tier host. WebSocket-driven classroom session (`/ws/classroom`). JWT auth, bcrypt, rotating refresh tokens, OTP email, rate limiting.

### 2.2 Existing Agent Orchestration
Explicit 7–8-state pedagogical FSM: `UNDERSTAND→PLAN→EXPLAIN→DEMONSTRATE→QUESTION→EVALUATE→ADAPT→CONTINUE`, with `ADAPT` branching to `ALLOW/MODIFY/REGENERATE/HUMAN`. Specialized agents (Planner, Explainer, Questioner, Adaptation Controller, Assessment Agent) sit behind an `OrchestratorFSM` + `SessionState`, calling an `LLM Adapter Facade` that routes to a Gemini adapter or an offline/mock fallback. This is a hand-rolled orchestration layer, not a graph framework — it is deliberately explicit per the architecture docs ("Teacher Agent must remain an explicit, inspectable state machine rather than becoming one giant LLM prompt").

### 2.3 Existing RAG
Document parsing (PDF/DOCX/PPTX/TXT) → semantic chunking → BGE-M3 hybrid (dense+sparse) embedding → Chroma vector store → Hybrid RRF retriever + cross-encoder reranker → query preprocessor/cache → a "Grounding Context Builder" producing `Contract.md`-formatted context blocks consumed by agent orchestration. This is a single-pass retrieval pipeline (retrieve once, hand to Planner/Explainer) — no iterative/self-correcting loop is evidenced.

### 2.4 Existing Persistence
SQLite WAL, SQLAlchemy models diagrammed: `users`, `lessons`, `lesson_nodes`, `interactions`, `reports`, `learner_profiles`, `documents`, `otp_codes`, `refresh_tokens`, `lesson_events`. `learner_profiles` is the closest existing thing to "memory," but its actual field contents are not evidenced beyond the name — the implementation agent must inspect it directly.

### 2.5 Existing Evaluation/Telemetry
`ml_core`: MCQ evaluator + Freeform rubric evaluator → Misconception Taxonomy Engine (subject-specific JSON taxonomies: physics/math/biology) → Semantic Misconception Matcher → Learner Mastery Engine (exponential moving average). Separate `mlops` module: `PerfTrace Instrumentor` + "Telemetry & Benchmark Logger" tracking latency for parsing/embedding/LLM/TTS/render/FFmpeg stages. This is real, existing observability infrastructure — but it is *performance/latency* tracing, not *agent-decision* tracing (no evidence it records retrieval evidence, prompts, or adaptation rationale as structured events).

### 2.6 Existing Contracts
`Contract.md` defines cross-module schemas: `LessonPlan`, `LessonNode`, `TeachingSegment`, `RenderedVideoSegment`, `InteractionEvent`, `StudentResponse`, `EvaluationResult`, `AdaptationDecision`, `AssessmentReport`. It is authoritative; contracts are versioned/locked *(inference from prior "contracts v1.0.0 locked" status note)*.

## 3. Modernization Goals
Make the agentic layer more capable (bounded iterative RAG, persistent pedagogical memory) and more legible (standardized tool access, structured decision tracing) — without discarding the working FSM, contracts, or the deterministic fallback path the project relies on for demo reliability and Gemini-quota safety.

## 4. Technology-by-Technology Analysis

### 4.1 LangGraph
- **A. Why:** The current FSM is already "stateful graph"-shaped (nodes, conditional edges, loops back from ADAPT to EXPLAIN). LangGraph's actual selling points — checkpointing/persistence, streaming state events, HITL interrupt — solve problems the project currently hand-rolls (SQLite session resume, WS event emission, HUMAN escalation as a manual branch). The risk is that LangGraph is a *runtime for graphs*, and the project's real value (explicit pedagogical semantics, deterministic fallback, Contract.md schemas) is orthogonal to which runtime executes the graph.
- **B. Where it integrates:** `ai_agent_orchestration`'s `OrchestratorFSM`/`SessionState` only. Should not touch `rag`, `ml_core`, `avatar_voice`, `backend` auth/persistence directly — those remain called *from* graph nodes, same as today.
- **C. What should NOT change:** The pedagogical state names/semantics (UNDERSTAND/PLAN/EXPLAIN/…/ADAPT), `Contract.md` schemas, the LLM Adapter Facade's Gemini/offline-fallback split, SQLite as the system of record, and the WS event contract the frontend already consumes.
- **D. Minimal viable integration:** Wrap the *existing* FSM transition functions as LangGraph nodes/edges in a **new, isolated module** (e.g., an orchestration adapter) that is invoked instead of the current dispatcher, while every node body still calls the existing Planner/Explainer/etc. functions unchanged. Persistence: use LangGraph's checkpointer only if it can write into the existing SQLite DB/tables without a schema fork *(implementation agent must verify)*; otherwise keep current SQLite session persistence as authoritative and treat LangGraph state as a transient runtime concern, checkpointed separately if needed.
- **E. Demonstrable value:** Judge can see the same teaching flow, but now resumable via LangGraph checkpoint replay, and adaptation loops visibly traced as graph steps rather than opaque function calls.
- **F. Complexity:** Medium — the mapping is conceptually direct, but interrupt/HITL for `HUMAN` escalation and compatibility with existing WS streaming both need careful adapter code.
- **G. Risks:** Framework lock-in; duplicated state (LangGraph's internal state vs. SQLite `SessionState`) causing drift; latency from an added abstraction layer; the explicit-FSM design principle in the project docs could be undermined if LangGraph's prompt-driven routing (if used) replaces deterministic transitions — must be avoided; new dependency footprint on a free-tier deploy *(interacts with memory constraints noted in earlier phases of this project)*.
- **H. Dependencies:** Should follow Phase 1 tracing foundation (§7) so graph-node execution is observable from day one; is a *prerequisite* for a clean Agentic RAG loop and MCP tool-calling if those are implemented as graph nodes rather than bolted onto the current dispatcher.
- **Verdict:** Justified as an **orchestration runtime substitution behind the same pedagogical semantics**, not an FSM replacement. Migration must be incremental: build the LangGraph adapter alongside the existing dispatcher, validate parity via offline tests, then cut over — never a hard rewrite.

### 4.2 MCP
- **A. Why:** Several existing capabilities (retrieval, learner profile read, lesson-state read, evaluation) are today direct Python calls between modules. Standardizing the *subset* that benefits from a stable, introspectable tool interface would make agent-tool boundaries explicit and testable, and would future-proof against needing a second LLM/agent framework or an external client later.
- **B. Where it integrates:** Only `ai_agent_orchestration`'s consumption of `rag` (retrieval) and `ml_core` (evaluation) plus any new pedagogical-memory reads (§4.4) are plausible MCP tool candidates. `backend` auth/session management, SQLite writes, and `avatar_voice` rendering should stay as direct internal calls — these are infrastructure, not agent-facing "tools" an LLM should be choosing to invoke.
- **C. What should NOT change:** Internal module APIs continue to exist as Python functions; MCP tool wrappers, where added, are a thin adapter layer on top, not a replacement of those functions. No MCP server should be exposed outside the deployed process without new auth review — out of scope here.
- **D. Minimal viable integration:** Expose 2–3 tools only where the agent genuinely benefits from *dynamically choosing whether to call something*, which is essentially only the Agentic RAG loop (§4.3): `search_knowledge`/`retrieve_source_chunk` as MCP tools consumed by the Explainer/RAG-refinement step. `get_student_profile`/`get_lesson_state` are *not* good MCP candidates now — they are read deterministically at fixed FSM points, not agent-chosen, so a direct function call remains simpler and lower-latency. `evaluate_answer`/`detect_misconception` also stay internal — they are deterministic pipeline stages, not agent-invoked tools.
- **E. Demonstrable value:** A trace showing an agent explicitly deciding to call `retrieve_source_chunk` again with a refined query, visible as a named tool call rather than an opaque internal retry.
- **F. Complexity:** Low for 1–2 tools; grows quickly if over-applied ("MCP everywhere" — explicitly rejected by this plan).
- **G. Risks:** Unnecessary abstraction/latency if used for deterministic (non-agent-chosen) calls; local MCP server adds a new process/IPC boundary on a memory-constrained deploy; validation/schema drift between the tool schema and `Contract.md`'s existing chunk/evidence schema.
- **H. Dependencies:** Should follow Agentic RAG design (§4.3) — MCP is the *interface* for that loop's tool calls, not an independent initiative. Also benefits from the tracing foundation (§7) existing first, so tool calls are logged uniformly.
- **Verdict:** Narrow, justified adoption — MCP-wrap only the RAG refinement tool-calls; everything else stays internal.

### 4.3 Agentic RAG
- **A. Why:** Current pipeline is single-pass: retrieve once per Planner/Explainer call, no sufficiency check, no refinement. This is the highest-leverage of the five areas because it directly touches the project's core grounding claim (evidenced concern from prior work in this project: "document influence on plan unproven," "0 sections," empty Grounding Evidence panel) and the RAG stack is otherwise mature (BGE-M3, RRF, reranker, citation threshold ≈0.52 *(inference from prior session)*).
- **B. Where it integrates:** `rag` module (adds a sufficiency-check + refinement step around the existing Hybrid RRF Retriever) and the `ai_agent_orchestration` PLAN/EXPLAIN nodes that consume its output. Does not touch `ml_core` or `avatar_voice`.
- **C. What should NOT change:** The embedding model, vector store, chunking strategy, reranker, and the existing citation-threshold/provenance mechanism — these remain the deterministic base case. The "topic-only, no document" path is unaffected.
- **D. Minimal viable integration:** Wrap the existing retrieval call in a bounded loop: retrieve → check sufficiency (e.g., top rerank score vs. existing citation threshold, or count of returned chunks) → if insufficient, refine query once (e.g., re-derive query from topic + unmet lesson-node concept) → retrieve again → stop. **Hard caps: max 2 refinement iterations, single confidence threshold reused from the existing citation threshold, deterministic fallback to the current single-pass result if the loop doesn't improve sufficiency.** No multi-hop graph traversal, no open-ended agentic loop.
- **E. Demonstrable value:** Visible in the (already-existing per prior UI work) Grounding Evidence panel: show "initial retrieval insufficient → refined query → N chunks now grounding this node," i.e., an observable two-step retrieval trace instead of a silent single call.
- **F. Complexity:** Medium — sufficiency scoring and query refinement are new logic, but sit cleanly around the existing retriever without touching its internals.
- **G. Risks:** Latency (each extra Gemini/embedding round-trip costs time and quota); runaway retrieval if caps aren't enforced; sufficiency threshold tuning could regress the already-fragile grounding-visibility issue noted earlier in this project.
- **H. Dependencies:** Benefits from tracing (§7) to make the loop's decisions demonstrable; can be built independent of LangGraph/MCP but is *cleanest* to express as a LangGraph subgraph or an MCP-tool-calling loop once those exist (§4.1, §4.2) — hence sequenced after Phase 2 orchestration work in §7, though a minimal version could ship earlier as a plain Python loop.
- **Verdict:** Strongly justified, bounded, and directly serves an already-known project weakness (grounding visibility).

### 4.4 Agent Memory / Pedagogical Memory
- **A. Why:** Personalization is a stated product goal (adaptive teaching), but "session" and "memory" are currently conflated — `SessionState`/`lesson_events` appear to be per-lesson working state, while `learner_profiles` *(inference — contents unconfirmed)* is the only plausible cross-lesson store.
- **B. Where it integrates:** `backend` persistence (extend/confirm `learner_profiles` schema), consumed by `ai_agent_orchestration`'s Planner (to bias node selection/difficulty) and Adaptation Controller (to recognize recurring misconceptions across lessons, not just within one).
- **C. What should NOT change:** Current lesson-scoped `SessionState`/FSM remains the authoritative in-lesson state; memory must never override it mid-lesson, only *inform* Planner decisions at lesson start or between lessons. No vector database for memory — SQLite is sufficient for structured facts (mastered/weak concepts, recurring misconceptions) which is what's actually needed, not semantic search over free text.
- **D. Minimal viable integration:** A small set of structured fields/rows keyed by student: mastered concepts, weak concepts, recurring misconception tags (reusing `ml_core`'s existing misconception taxonomy vocabulary, not a new one), last N adaptation outcomes. **Written** at lesson/assessment completion (from `AssessmentReport`/`EvaluationResult` — reuse existing contracts, don't invent new evaluation output). **Read** once, at lesson-plan generation time, by the Planner. No mid-lesson memory writes/reads beyond the existing FSM state. Explicitly exclude: raw transcripts, full conversation history, anything not needed for planning bias — minimizes storage and privacy surface.
- **E. Demonstrable value:** A student who previously showed a "confuses net force with total force" misconception (per taxonomy) gets a lesson plan on a related topic that proactively addresses it — observable as a plan-level note, not hidden state.
- **F. Complexity:** Low–Medium — mostly schema + two read/write points; no new infra.
- **G. Risks:** Privacy (student data persisting beyond a session — needs explicit inclusion in existing security boundaries, not a new auth model); stale memory biasing a plan incorrectly if not scoped/decayed; scope creep into a full "user modeling" system.
- **H. Dependencies:** Independent of LangGraph/MCP/Agentic RAG; can be implemented in parallel, but should reuse `ml_core`'s existing misconception vocabulary (confirm it's stable before building on it) and the existing `AssessmentReport` contract fields (`strong_areas`, `weak_areas`, `recommended_next` per Contract.md) rather than duplicating that taxonomy.
- **Verdict:** Justified as a narrow, SQLite-based, structured extension — not a new memory subsystem or vector store.

### 4.5 Agent Evals & Tracing / Observability
- **A. Why:** `mlops`'s `PerfTrace`/Telemetry Logger already tracks *latency* per pipeline stage but not *decisions* (what was retrieved, why a plan looked the way it did, why ADAPT chose REGENERATE). Without decision-level tracing, none of the other four technologies (LangGraph state transitions, MCP tool calls, Agentic RAG refinement, memory reads) are demonstrable or debuggable.
- **B. Where it integrates:** Extends `mlops` (reuse its existing instrumentation pattern) with event emission points added at: Planner decision, RAG retrieval (incl. refinement iterations from §4.3), Explainer output, Questioner output, EvaluationResult, AdaptationDecision, memory read/write (§4.4), and MCP tool calls if adopted (§4.2). Does not touch `avatar_voice` FFmpeg-level tracing (already covered by existing PerfTrace).
- **C. What should NOT change:** No existing latency-tracing behavior is removed; this is additive event logging alongside it, using the same SQLite persistence (a new `agent_events`-style table, structure TBD by implementation agent after inspecting existing `lesson_events`/`interactions` tables — may already be adequate).
- **D. Minimal viable integration:** A single structured "agent trace event" written at each of the 7 points above: `{event_type, session_id, node_id, timestamp, structured_payload}` where payload is **observable metadata only** — retrieved chunk IDs/scores, not prompts; decision + reason code, not full LLM output; token/latency counts if cheaply available from existing PerfTrace. No hidden chain-of-thought is logged or displayed. A minimal frontend/API surface to read these events back (could reuse the existing "AI Inspector" panel pattern *(inference from prior session's classroom screenshots)* rather than building a new observability UI).
- **E. Demonstrable value:** A judge can open a trace and see: retrieval → sufficiency check → (optional refinement) → plan → explanation → question → evaluation → adaptation decision, as a readable structured sequence — this is the connective tissue that makes §4.1–4.4 demo-able at all.
- **F. Complexity:** Low–Medium — mostly a logging convention + minimal storage/read path, reusing existing telemetry infra rather than adopting a tracing platform (e.g., LangSmith/OpenTelemetry) which would add external dependencies/cost not justified for a hackathon-scale deploy.
- **G. Risks:** Log volume/storage growth on SQLite; over-instrumenting adds latency; risk of accidentally logging sensitive content (prompts, PII) if payload isn't scoped carefully — must be enforced by convention/review.
- **H. Dependencies:** None — this should be **Phase 1**, before LangGraph/MCP/Agentic RAG/Memory, because every other phase's value is unverifiable without it.
- **Verdict:** Foundational; a lightweight custom event log is sufficient — no heavyweight observability platform is justified at this scale.

## 5. Additional Logical Technologies
- **Structured agent outputs (Pydantic-enforced tool/LLM outputs):** Already implied by existing `Contract.md` schemas for `TeachingSegment`/`EvaluationResult`/etc. *(inference)*. Not a new initiative — just ensure any new outputs from §4.1–4.5 (sufficiency check, memory reads, trace events) are Pydantic-validated the same way. **Include now, as a cross-cutting convention, not a separate phase.**
- **Agent guardrails / fallback reliability:** The project already has an LLM Adapter Facade with an offline fallback — extending this pattern (bounded retries, deterministic fallback) to the Agentic RAG loop (§4.3) and any MCP tool calls (§4.2) is directly reusing an existing pattern, not a new technology. **Include as an implementation rule within §4.2/§4.3, not a separate phase.**
- **A2A (Agent-to-Agent protocol):** Shikshak's "agents" (Planner, Explainer, Questioner, Adaptation Controller, Assessment) are internal Python components within one process/orchestrator, not independent services needing cross-process/cross-vendor interoperability. There is no evidence of multiple deployed agent services that need to negotiate capabilities with each other or with external agents. **Explicitly future scope — do not implement.**
- **Semantic caching, model routing:** No evidence of multiple LLM backends needing routing beyond the existing Gemini/offline-fallback split, and semantic caching over retrieval queries would add complexity disproportionate to the current single-pass→bounded-loop RAG change. **Future scope.**
- **Structured event streaming (beyond existing WS):** The existing WS channel already streams FSM/session events to the frontend; §4.5's trace events can ride the same channel or the same SQLite-backed read path rather than introducing a new streaming layer. **Not a separate technology — folded into §4.5.**

## 6. Recommended Target Architecture
```
Student
  ↓
Frontend (WS)
  ↓
FastAPI Gateway
  ↓
Pedagogical Session State (SQLite, unchanged)
  ↓
Orchestration runtime (existing dispatcher → optionally LangGraph adapter, Phase 2)
  ├── Planner  ──┐
  ├── Explainer  ├── read: Pedagogical Memory (SQLite, Phase-appropriate)
  ├── Questioner │
  └── Adaptation ─┘
  ↓
Agentic RAG loop (bounded: retrieve → sufficiency check → ≤1 refine → stop)
  exposed via MCP tools ONLY for this loop's tool-calls (search_knowledge, retrieve_source_chunk)
  ↓
ML Core (evaluation, misconception detection — unchanged)
  ↓
Adaptation Decision (ALLOW/MODIFY/REGENERATE/HUMAN — unchanged semantics)
  ↓
Agent Trace Events (written alongside every step above, Phase 1 foundation)
  ↓
Avatar/Voice + Assessment (unchanged)
```
Every box above is additive to, or a thin wrapper around, an existing module. No existing module is replaced wholesale.

## 7. Phase-wise Implementation Plan

### Phase 0 — Baseline & Contract Audit
- **Objective:** Confirm exact current state before any change.
- **Tasks:** Inspect `Contract.md`, actual `ai_agent_orchestration` dispatcher, `learner_profiles` schema, `mlops` telemetry structure, existing WS event types. Produce a short findings note (no code).
- **Modules affected:** None (read-only).
- **Complexity/Risk:** Low/Low. **Dependencies:** None.
- **Acceptance criteria:** Findings note confirms or corrects every *(inference)* item in §2 and §4 of this plan.
- **Validation:** N/A (read-only). **Human validation:** Review findings note before Phase 1 starts.
- **Not included:** Any code change.

### Phase 1 — Agent Trace/Eval Foundation (§4.5)
- **Objective:** Add structured, observable agent-decision event logging.
- **Tasks:** Design minimal `agent_events`-style schema (reuse existing tables if adequate per Phase 0 findings); add event emission at Planner/RAG/Explainer/Questioner/Evaluation/Adaptation points using existing pipeline call sites; expose read path (extend existing AI Inspector-style panel if present, else a minimal read endpoint).
- **Modules affected:** `mlops`, touch points in `ai_agent_orchestration`, `rag`, `ml_core` (adding event calls only, no logic change).
- **New abstractions:** One trace-event writer function/module.
- **Judge-visible improvement:** A readable trace of agent decisions for any lesson.
- **Complexity:** Low–Medium. **Risk:** Low (additive only).
- **Dependencies:** Phase 0.
- **Acceptance criteria:** Every subsequent phase's new decisions (RAG refinement, memory reads, graph transitions, MCP calls) are traceable once built.
- **Offline/static validation:** Schema validation of event payloads; unit test with a stub pipeline confirming events are written at each point.
- **Human validation:** Run one real lesson, inspect the trace for completeness/no leaked prompts or secrets.
- **Not included:** External observability platform integration; UI redesign.

### Phase 2 — LangGraph Orchestration Adapter (§4.1)
- **Objective:** Re-express the existing FSM as a LangGraph-executed graph without changing pedagogical semantics.
- **Tasks:** Build an isolated adapter module wrapping existing node functions as LangGraph nodes/edges; validate parity against the current dispatcher via offline tests; decide checkpoint storage (LangGraph checkpointer vs. existing SQLite `SessionState`) per Phase 0 findings; wire HUMAN escalation as interrupt only if it demonstrably simplifies the existing branch (else keep current branch code).
- **Modules affected:** `ai_agent_orchestration` only.
- **New abstractions:** LangGraph adapter module; parity test harness.
- **Judge-visible improvement:** Same teaching flow, now resumable via graph checkpoint; trace events (Phase 1) show graph-node execution.
- **Complexity:** Medium. **Risk:** Medium (touches core orchestration; must not regress FSM correctness).
- **Dependencies:** Phase 1 (for parity verification via traces), Phase 0.
- **Acceptance criteria:** Every existing FSM transition and ADAPT branch behaves identically under the new adapter (verified via offline parity tests); old dispatcher path remains available as fallback until cutover is approved.
- **Offline/static validation:** Parity unit tests comparing old vs. new dispatcher outputs on identical fixture inputs; schema/type checks.
- **Human validation:** One full live lesson including a forced MODIFY→REGENERATE→HUMAN path.
- **Not included:** Prompt-driven/non-deterministic routing; replacing pedagogical state names/semantics.

### Phase 3 — Agentic RAG (§4.3)
- **Objective:** Add bounded sufficiency-check + refinement to retrieval.
- **Tasks:** Add sufficiency scoring (reuse existing citation-threshold concept) around existing Hybrid RRF Retriever; add single-iteration query refinement; enforce hard caps (≤2 iterations); wire trace events (Phase 1) for each retrieval attempt; surface result in existing Grounding Evidence UI slot if present *(per prior project context)*.
- **Modules affected:** `rag`, call sites in `ai_agent_orchestration` (Planner/Explainer).
- **New abstractions:** Sufficiency-check function; refinement-query builder.
- **Judge-visible improvement:** Visible "insufficient → refined → grounded" trace for weakly-covered topics.
- **Complexity:** Medium. **Risk:** Medium (latency, Gemini-quota use for refinement query generation).
- **Dependencies:** Phase 1 (tracing); benefits from, but does not strictly require, Phase 2.
- **Acceptance criteria:** Loop never exceeds cap; always falls back to current single-pass result if refinement doesn't improve sufficiency; existing topic-only (no-document) path unaffected.
- **Offline/static validation:** Stub-retriever test proving cap enforcement and fallback behavior; contract validation on grounding context output.
- **Human validation:** Compare grounding quality on a weakly-covered vs. well-covered document topic.
- **Not included:** Multi-hop graph retrieval; unbounded iteration.

### Phase 4 — MCP Tool Layer for RAG (§4.2)
- **Objective:** Wrap only the Agentic RAG tool-calls as MCP tools.
- **Tasks:** Define `search_knowledge`/`retrieve_source_chunk` MCP tool schemas matching existing chunk/evidence contract fields; wire the Phase 3 refinement loop to call them instead of the raw retriever function directly; trace tool calls via Phase 1 events.
- **Modules affected:** `rag` (tool wrapper only), `ai_agent_orchestration` (consumption point).
- **New abstractions:** MCP tool schema + local server/adapter.
- **Judge-visible improvement:** Trace shows named tool invocations for retrieval steps.
- **Complexity:** Low–Medium. **Risk:** Medium (new process/IPC boundary on constrained deploy — verify memory/latency impact before committing).
- **Dependencies:** Phase 3 (nothing to wrap without it), Phase 1.
- **Acceptance criteria:** Tool schema validated against existing chunk metadata contract; no change in retrieval correctness vs. Phase 3's direct-call version; measured latency overhead acceptable *(threshold to be set after Phase 0 findings on deploy constraints)*.
- **Offline/static validation:** Schema validation; mock MCP client/server round-trip test.
- **Human validation:** Confirm no perceptible latency regression in a live lesson.
- **Not included:** MCP-wrapping learner profile, lesson state, or evaluation — those stay internal calls.

### Phase 5 — Pedagogical Memory (§4.4)
- **Objective:** Add structured, cross-lesson memory read at planning time and write at assessment time.
- **Tasks:** Confirm/extend `learner_profiles` schema (mastered/weak concepts, recurring misconception tags reusing existing taxonomy, last-N adaptation outcomes); add read call in Planner (lesson-start only); add write call at assessment completion (reusing `AssessmentReport`/`EvaluationResult` contract fields); trace reads/writes via Phase 1.
- **Modules affected:** `backend` (schema), `ai_agent_orchestration` (Planner read, Assessment write).
- **New abstractions:** Memory read/write functions; none new for storage (SQLite reused).
- **Judge-visible improvement:** A second lesson for the same student on a related topic visibly reflects prior weak areas/misconceptions in the generated plan.
- **Complexity:** Low–Medium. **Risk:** Low–Medium (privacy scope, stale-memory bias).
- **Dependencies:** Phase 1 (tracing); independent of Phases 2–4.
- **Acceptance criteria:** Memory never mutates mid-lesson `SessionState`; only read once at plan time; write only from finalized assessment data, not intermediate/speculative state.
- **Offline/static validation:** Schema/contract validation; unit test confirming memory read only occurs pre-PLAN and write only post-assessment.
- **Human validation:** Complete two lessons for one student on related topics; confirm plan #2 reflects lesson #1 outcomes.
- **Not included:** Vector-based memory search; full conversation/transcript storage; cross-student memory sharing.

### Phase 6 — Integration, Stabilization, Demo Validation
- **Objective:** Verify all phases work together without regression.
- **Tasks:** End-to-end offline test pass across FSM+RAG+MCP+memory+tracing; confirm existing contracts unchanged/compatibly extended; confirm fallback paths (offline LLM adapter, single-pass RAG, no-memory case) still function.
- **Modules affected:** All touched above (verification only, minimal fixes).
- **Complexity:** Medium (integration surface). **Risk:** Medium (compounding of prior phases' risk).
- **Dependencies:** Phases 1–5 complete.
- **Acceptance criteria:** Per §14 Definition of Done below.
- **Offline/static validation:** Full offline/deterministic test suite for touched modules (not entire repo blindly — targeted).
- **Human validation:** Full live lesson run per §13 demo scenarios.
- **Not included:** New feature work; scope is stabilization only.

## 8. Priority Matrix
- **Must Have:** Phase 1 (Tracing foundation), Phase 3 (Agentic RAG, bounded) — directly serves the project's known grounding-visibility gap.
- **Should Have:** Phase 5 (Pedagogical Memory, SQLite-only) — strong personalization value, low infra cost, independent of the riskier orchestration change.
- **Could Have:** Phase 2 (LangGraph adapter) — valuable for checkpointing/legibility but is the highest-risk touch to core orchestration; can be deferred without blocking Phases 3/5 if those are implemented as plain bounded loops instead of graph nodes.
- **Future Scope:** Phase 4 (MCP tool layer) — real but narrow value, adds a process/IPC boundary on a constrained deploy; A2A; semantic caching; model routing; full observability platform migration.

## 9. Contract & Compatibility Requirements
- Read `Contract.md` before any change touching cross-module data.
- New fields (sufficiency scores, trace events, memory records, MCP tool schemas) must be **additive/optional** to existing contracts — never remove or rename existing fields.
- Any genuinely required contract change (e.g., extending `AssessmentReport` consumption for memory writes) must be flagged explicitly for human approval before implementation, with the affected modules listed.
- No module duplicates another module's business logic (e.g., MCP tool wrapper must call the existing `rag` retriever, not reimplement retrieval).

## 10. Security Requirements
- Never open, read, print, or copy the Gemini API key or any `.env` contents.
- Never commit secrets; never call Gemini or any external LLM/API during implementation or automated testing.
- Never send repository contents to external AI APIs (including any MCP server that might otherwise be exposed externally — keep local/offline only).
- All live LLM/API/browser testing is performed by the human separately; implementation agent uses only static/offline/deterministic checks.
- No git commands executed by the implementation agent unless explicitly authorized; provide exact commands for human review instead.

## 11. Token-Efficient Implementation Rules
Inspect only relevant files first; avoid dumping entire files or repository-wide scans; use targeted searches; avoid repeating already-known information; make one logical change at a time; reuse existing abstractions (LLM Adapter Facade, PerfTrace pattern, existing taxonomy); avoid unnecessary new dependencies; avoid speculative refactoring; run only targeted checks after each logical change; keep progress summaries concise; avoid unnecessary full-suite test execution; avoid regenerating unchanged files. Temporary files under `current_task/` are not committed unless explicitly requested.

## 12. Testing & Validation Strategy
Per phase, prefer targeted over exhaustive checks:
- **Static checks (every phase):** Python syntax/imports, Pydantic/contract schema validation, deterministic unit tests scoped to touched modules only.
- **Integration checks (Phases 2, 3, 4, 6 only):** Parity tests (Phase 2), bounded-loop cap/fallback tests (Phase 3), mock tool round-trip (Phase 4), cross-phase offline test pass (Phase 6).
- **Human validation (all phases, separately performed):** Live lesson runs exercising the specific new behavior — frontend behavior, live LLM output quality, RAG grounding correctness, adaptive teaching correctness, memory effect across two lessons, trace completeness. Never substituted by the implementation agent running live API calls itself.

## 13. Demo / Judge Validation
- **Demo 1 — Agentic RAG:** Show a topic where initial retrieval is weak; trace (Phase 1+3) displays "insufficient → refined query → sufficient," then a grounded explanation.
- **Demo 2 — Stateful Agent Workflow:** Show the pedagogical state sequence and a live MODIFY→REGENERATE→HUMAN adaptation loop, either via existing dispatcher or the Phase 2 LangGraph adapter.
- **Demo 3 — Agent Memory:** Run two lessons for one student on related topics; show lesson #2's plan referencing lesson #1's weak areas/misconceptions.
- **Demo 4 — MCP:** Show a trace entry naming the exact tool call (`retrieve_source_chunk`) rather than an opaque internal function call, if Phase 4 is implemented.
- **Demo 5 — Tracing/Evaluation:** Show the full structured event sequence for one lesson segment: retrieval metadata → plan decision → evaluation result → adaptation decision — observable events only, no raw chain-of-thought or prompt text exposed.

## 14. Definition of Done
- Existing teaching flow (FSM states, WS events, contracts) still functions identically for a student with no memory history and no forced adaptation.
- Pedagogical states remain semantically correct and named as before.
- Agent decisions (retrieval, plan, evaluation, adaptation) are traceable as structured events without exposing hidden chain-of-thought.
- RAG performs bounded iterative retrieval only when initial retrieval is insufficient, always falls back to the deterministic single-pass result, never exceeds the configured iteration cap.
- Any MCP tools present have clearly defined, contract-aligned schemas and are scoped to the RAG refinement loop only.
- Learner memory influences future lesson planning only at plan-generation time, never mid-lesson, and only from finalized assessment data.
- Adaptation decisions (ALLOW/MODIFY/REGENERATE/HUMAN) remain evaluable via trace events with unchanged semantics.
- Human escalation path remains functional end-to-end.
- No Gemini API key/`.env` access and no live external API calls were performed by any implementation agent.
- All existing module contracts (`Contract.md`) remain valid; any changes are additive and explicitly approved.
- The system remains usable via its existing offline/deterministic fallback (LLM Adapter Facade offline mode; single-pass RAG if agentic loop is disabled/capped out).
- No duplicate framework/abstraction was introduced where an existing one already served the purpose.

## 15. Instructions for the Implementation Agent
Adopt the role matching the active phase: Senior Agentic AI Engineer (Phase 1, 6), LangGraph Architect (Phase 2), RAG/Information Retrieval Engineer (Phase 3), MCP Integration Engineer (Phase 4), ML/AI Evaluation Engineer (Phase 5, memory+eval aspects), Backend/Systems Engineer (schema work across phases).

Rules, all phases:
1. First inspect the relevant existing files for that phase only — do not re-inspect files already covered by Phase 0's findings note.
2. Understand current implementation before changing anything; do not assume this document's *(inference)* items are fact — confirm in code first.
3. Follow repository specifications and `Contract.md`; identify affected contracts before coding; preserve existing public schemas; update contracts only when justified and explicitly flagged for approval.
4. Avoid unnecessary refactoring; work incrementally, one logical change at a time; keep changes scoped to the approved phase only.
5. Prefer minimal, maintainable changes; reuse existing abstractions (LLM Adapter Facade, PerfTrace pattern, existing misconception taxonomy) rather than introducing new ones.
6. Never access `.env` secrets; never call Gemini or any external LLM/API; use only deterministic/offline validation; do not execute git commands unless explicitly authorized — provide human-readable commands instead.
7. Provide concise, targeted progress summaries after each logical change, not full-file dumps.
8. Stop and ask for clarification if the actual repository contradicts this plan's architecture/contract assumptions in a way that affects public interfaces — do not silently resolve the discrepancy.

## 16. Deferred Ideas
A2A protocol (no independent cross-process agents exist to justify it); semantic caching over retrieval queries; model routing across multiple LLM backends; full observability/tracing platform (e.g., LangSmith, OpenTelemetry) in place of the lightweight custom event log; vector-based/semantic pedagogical memory; MCP-wrapping learner-profile/lesson-state/evaluation calls; LangGraph-driven prompt-based (non-deterministic) routing in place of explicit FSM transitions; cross-student memory sharing; full conversation/transcript-level memory storage.
