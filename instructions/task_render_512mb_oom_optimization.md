# Render 512 MB OOM — Diagnosis & Optimization Task

## 1. Objective

Diagnose and resolve Out-of-Memory (OOM) crashes of the deployed **Shikshak AI** application
on a Render instance limited to **512 MB RAM**, without changing the existing public Render
URL, frontend, API contracts, or the demoable teaching workflow (RAG, video, adaptation).
Follow strict measure-first discipline: no component may be rewritten or replaced until it is
confirmed, via instrumentation, to be a dominant contributor to peak memory.

---

## 2. Current Deployment Situation

### 2.1 Observed Behavior
1. Topic-only lesson generation (no uploaded document) → works, no crash.
2. Document-upload lesson generation → OOM crash.
3. Opening a lesson and triggering video generation → OOM crash.

These three data points are the only confirmed production symptoms. They imply the document/RAG
ingestion path and the video/avatar pipeline are each independently capable of exceeding
available memory; the topic-only path (Planner/Explainer/Gemini/no-document-RAG) is not.

### 2.2 Deployment Constraints
- Render instance RAM ceiling: **512 MB**.
- The existing Render URL is **already submitted for hackathon judging** — it must keep working
  at the same URL, same frontend, same API/WebSocket contracts.
- Internal implementation is free to change; externally visible behavior must not regress.
- A lighter production/demo-mode implementation is acceptable if user-facing functionality is
  equivalent.

### 2.3 Current Technology Stack (per supplied docs/diagrams — to be verified against live repo)
- Frontend: Vanilla HTML5/CSS3/JS SPA served by the backend.
- Backend: FastAPI, Python 3.10+, WebSockets, Pydantic, SQLite (WAL) via SQLAlchemy.
- AI Orchestration: 7-state FSM (Understand→Plan→Explain→Demonstrate→Question→Evaluate→Adapt→
  Continue/Human), Planner/Explainer/Questioner/Adaptation Controller/Assessment agents, Gemini
  LLM Adapter with an offline SmartMock fallback.
- RAG module: DocumentParser (PDF/DOCX/PPTX/TXT) → Semantic Chunker → **BGE-M3 embedder**
  (dense 1024-d + sparse/SPLADE) → **ChromaDB** vector store → Hybrid RRF Retriever +
  **cross-encoder reranker** → Query cache → Grounding Context Builder.
- ML Core: MCQ evaluator, freeform rubric evaluator, misconception taxonomy matcher (JSON
  taxonomies: physics/math/biology), learner mastery engine.
- Avatar/Voice: Edge-TTS (remote neural TTS) → Viseme/WebVTT aligner → Visual board renderers
  (LaTeX/EquationRenderer, Matplotlib GraphRenderer, Graphviz DiagramRenderer, Pygments
  CodeRenderer, TakeawayRenderer) → **FFmpeg** 1080p 24 FPS multi-stream compositor.
- MLOps: PerfTrace instrumentor (latency tracing / TimedBlock) already present per architecture
  diagram — an existing hook that may be extensible for memory instrumentation.
- Security: JWT + rotating refresh tokens, bcrypt, OTP.

### 2.4 Existing Architecture Relevant to Memory
- The RAG module (`modules/rag/`) is the only place BGE-M3 and the cross-encoder reranker and
  ChromaDB are referenced. Document-only crash strongly points at this module's active code
  path, but the exact call graph, load timing, and singleton/caching behavior are **not
  established from the supplied docs** — must be inspected in the live repo.
- The avatar_voice module (`modules/avatar_voice/`) owns TTS, viseme generation, all visual
  renderers, and the FFmpeg compositor. Video-only crash points here, but which specific stage
  (renderer buffers vs. FFmpeg subprocess vs. frame retention) is unknown.
- `instructions/Contract.md` defines all cross-module JSON contracts (`ParsedDocument`,
  `LessonPlan`, `TeachingSegment`, `RenderedVideoSegment`, etc.) and explicit `AvatarAdapter`,
  `TTSAdapter`, `VectorStoreAdapter`, `LLMAdapter` interfaces — these adapter seams are the
  natural insertion points for swapping a heavy local implementation for a lighter one without
  touching orchestration logic.
- `08_Folder_Structure.md` confirms strict module ownership: no agent may edit another module's
  `src/` without a logged Contract change.
- Deployment/runtime config (worker count, Gunicorn/Uvicorn settings, `render.yaml`/Procfile,
  lazy vs eager model loading) is **not present in the supplied docs** — must be inspected
  directly.

---

## 3. Confirmed Facts vs Hypotheses

### Confirmed
- Topic-only generation does not crash; document generation and video generation each crash
  independently, on the same 512 MB instance.
- RAG pipeline (document path) includes BGE-M3 embedding, ChromaDB, hybrid RRF retrieval, and a
  cross-encoder reranker (per architecture diagram and README).
- Video pipeline includes Edge-TTS, multiple visual renderers, and an FFmpeg 1080p compositor.
- Gemini and Edge-TTS are remote/API-based; their model weights should not occupy Render process
  RAM, but request/response payloads, generated audio, and any buffered content still count
  against application memory.
- `Contract.md` defines explicit `VectorStoreAdapter`, `TTSAdapter`, `AvatarAdapter`,
  `LLMAdapter` interfaces intended to keep vendor/implementation swaps localized.

### Suspected (plausible, NOT established)
- BGE-M3 (~569M params) may be loaded locally in-process rather than called remotely; if so it
  is very likely the dominant document-path contributor on a 512 MB instance.
- The cross-encoder reranker may be a second local model loaded alongside BGE-M3.
- ChromaDB in-process storage/index may hold non-trivial memory depending on corpus size, though
  for a hackathon-scale demo corpus this is less likely to dominate versus the embedder itself.
- Video path: Matplotlib figures not explicitly closed, all frames generated and retained before
  FFmpeg invocation (batch instead of streaming), or FFmpeg subprocess memory could each be the
  dominant contributor — cannot be distinguished without measurement.
- Multiple Uvicorn/Gunicorn workers, each loading BGE-M3/reranker independently, could multiply
  baseline memory even before any request.

### Unknown / Requires Measurement or Repository Inspection
- Whether BGE-M3 and the reranker are loaded eagerly at startup or lazily on first request.
- Whether they are loaded once per process or once per worker (worker count itself is unknown).
- Exact ChromaDB persistence mode and current collection size in the deployed demo.
- Whether video frames/images are held in Python memory simultaneously or streamed to disk
  incrementally.
- Whether FFmpeg is invoked once per full video or per-segment, and its native memory footprint
  on the current demo video length/resolution.
- The current Render service's worker/process configuration (Procfile, `render.yaml`, or Start
  Command).
- Whether concurrent requests are possible and whether that multiplies peak memory.

---

## 4. Memory Risk Analysis

### 4.1 BGE-M3
Large embedding model (~569M parameters; local full-precision footprint plausibly in the
multi-hundred-MB to >1–2 GB range depending on representation/runtime and whether dense+sparse
heads are both loaded). If loaded in-process on a 512 MB instance, this alone could explain the
document-path OOM. Must confirm: is it loaded locally at all in the deployed configuration, and
when.

### 4.2 Reranker (cross-encoder)
A second potentially-heavy local model. Even if smaller than BGE-M3, loading it alongside BGE-M3
compounds memory pressure. Determine whether it's local, when it loads, and whether it is
strictly necessary for demo-quality retrieval.

### 4.3 ChromaDB
Memory depends on collection size, vector dimensionality (1024-d per architecture diagram),
metadata volume, and persistence mode (in-memory vs. on-disk with mmap). For a small hackathon
demo corpus this is unlikely to dominate but must still be measured, especially if the deployed
instance keeps stale/duplicate collections from repeated testing.

### 4.4 Document Processing
Potential coexistence of multiple large intermediate objects: raw uploaded file bytes, extracted
full text, page/section structures, all chunks, all embeddings, before/while insertion into
Chroma. If the pipeline holds the "whole document" fully expanded at every stage simultaneously
rather than streaming/releasing intermediates, peak memory could spike well above what any single
stage requires alone — independent of model size.

### 4.5 Video Pipeline (general)
Multi-stage generation (TTS → visemes → N visual renderers → FFmpeg) with several candidate
sources of peak memory: audio buffers, unclosed Matplotlib figures, retained frame arrays,
simultaneous multi-stream compositing inputs.

### 4.6 FFmpeg
Native subprocess memory is invisible to Python-level tools (`tracemalloc`, and often to naive
`psutil` parent-process RSS checks unless the child process is measured explicitly). Resolution
(1080p), FPS (24), duration, and number of simultaneous input streams (main board + avatar PiP +
subtitles + audio mux per architecture diagram) all affect its footprint.

### 4.7 Workers / Concurrency
If Uvicorn/Gunicorn is configured with >1 worker, any in-process model (BGE-M3, reranker) is
plausibly duplicated per worker, multiplying baseline memory before any request arrives. This is
a common, easily-overlooked cause of OOM on small instances and must be checked early since it is
cheap to verify and cheap to fix if confirmed.

### 4.8 Other Potential Contributors
- Query/result caching (5-min TTL cache per architecture diagram) retaining large payloads.
- SQLite WAL file growth (unlikely to be a RAM issue, but verify no full-table loads into memory).
- Session/WebSocket state objects retaining full lesson/video payloads in memory per active
  session.
- Any global/module-level singleton that accumulates state across requests without cleanup.

---

## 5. Diagnostic / Profiling Plan

### Render Metrics
Use Render's built-in service memory graph to capture, for each of the following moments,
timestamped RAM readings: idle/startup, immediately before a document-upload lesson request,
peak during that request, immediately after, immediately before a video-generation request, peak
during that request, immediately after. This is the ground-truth signal for whether the fix
actually works in production and must bookend every experiment below.

### psutil RSS
Add lightweight instrumentation using `psutil.Process(os.getpid()).memory_info().rss` at a
**small, deliberately chosen set of checkpoints** rather than every function. Recommended
checkpoint set (confirm against actual pipeline code before finalizing):
- App startup (post-import, pre-first-request) — reveals whether heavy models load eagerly.
- Document upload received / file loaded into memory.
- After text extraction.
- After chunking.
- After embedding generation (dense + sparse).
- After Chroma insertion.
- After retrieval + reranking for a query.
- Lesson generation complete.
- TTS synthesis complete.
- After each visual renderer stage completes (or after all renderers, if per-renderer is too
  granular for a first pass).
- FFmpeg subprocess invocation start.
- FFmpeg subprocess completion.
- Request/response fully complete.

RSS is the right primary signal here because it captures the process's actual resident memory
including native/C-extension allocations (NumPy, PyTorch/ONNX runtime backing BGE-M3, FFmpeg's
Python wrapper overhead, etc.) — the same thing Render's OOM killer acts on — rather than only
Python-heap allocations.

### tracemalloc
Use `tracemalloc` snapshots at 2–3 of the highest-suspicion checkpoints (e.g. before/after
embedding generation, before/after chunking) to see which Python-level objects/lines are
growing. Explicitly document that `tracemalloc` will **not** capture: native library allocations
(e.g. the actual embedding model's tensor memory if it's backed by a C/C++ runtime), ML
framework internal allocations, subprocess memory (FFmpeg), or any other non-Python allocation.
It is a supplementary tool for the Python-object-retention hypothesis only, never sufficient
alone.

### Native/FFmpeg Memory
Measure the FFmpeg subprocess's own RSS separately (e.g. via `psutil.Process(child_pid)` once the
subprocess handle is available, or OS-level tools during a local reproduction) rather than
inferring it from the parent Python process alone.

### Controlled Experiments
Run the smallest set of experiments that can discriminate between the live hypotheses. Bookend
every experiment with Render-metrics readings plus the psutil checkpoints above.

- **Test A — Startup baseline**: Deploy, measure idle memory immediately and 60s after startup
  (to catch any delayed/background model loading).
- **Test B — Topic-only lesson**: Confirms current known-good baseline; establishes the memory
  floor for orchestration + Gemini + no-RAG.
- **Test C — Small document**: Smallest realistic document (e.g. 1–2 pages). If this alone OOMs
  or spikes sharply, the fixed cost of loading BGE-M3/reranker is the likely dominant factor
  (not document size).
- **Test D — Larger document**: If Test C succeeds but a larger document fails or spikes further,
  memory scales with content size — points at chunk/embedding-count-driven growth or
  non-streaming intermediate retention (§4.4) rather than fixed model-loading cost.
- **Test E — RAG pipeline in isolation (no video)**: Run ingestion→retrieval→reranking and stop
  before video generation, to cleanly separate document-path memory from video-path memory (the
  production symptom already suggests these are somewhat independent, but confirm).
- **Test F — Video generation in isolation**: Use an already-generated lesson/script (bypass
  document RAG) and trigger only TTS→visuals→FFmpeg, to isolate video-path memory from RAG-path
  memory.
- **Test G — Worker/concurrency check**: Inspect deployment start command / Procfile for worker
  count; if >1, this alone may explain why a functioning single-process budget still OOMs in
  production — cheap to check, potentially high-impact, do this early (can be folded into Phase
  0 rather than requiring a live experiment).

Do not add additional experiments beyond A–G unless results are genuinely ambiguous between two
remaining hypotheses.

---

## 6. Decision Tree for Identifying the Bottleneck

```
Start: run Test A (baseline) and inspect worker config (Test G)
   ↓
If worker count > 1 AND any model loads per-worker
   → high-confidence contributor; note it, but still complete B–F before deciding sole fix
   ↓
Run Test B (topic-only) — expected to pass; confirms instrumentation works correctly
   ↓
Run Test C (small document)
   If RSS jumps sharply right at "after embedding generation" checkpoint, roughly independent
   of document size
       → BGE-M3 / reranker local loading is the primary suspect (§4.1, §4.2)
   If RSS grows steadily across "chunking" → "embedding" → "Chroma insertion" checkpoints,
   proportional to content size
       → run Test D to confirm scaling
       → if confirmed, document-processing intermediate retention (§4.4) or per-chunk embedding
         batching is the primary suspect, independent of or in addition to model size
   ↓
Run Test E to confirm RAG-only memory profile matches C/D findings without video interference
   ↓
Run Test F (video isolation)
   If RSS jumps at "TTS complete" → audio buffer handling
   If RSS jumps incrementally across renderer checkpoints and is NOT released between them
       → renderer cleanup / frame retention (§4.5) is the primary suspect
   If RSS jumps sharply only at "FFmpeg start"/"FFmpeg completion" in the FFmpeg child process
   specifically
       → FFmpeg native memory (§4.6) is the primary suspect — investigate resolution/streaming
         input strategy rather than assuming code-level Python fix
   ↓
Cross-reference all findings against Render-level metrics from each test to confirm the
Python/psutil-observed spike corresponds to the actual OOM-triggering peak in production.
```
Adjust this tree once real repository structure and measurements are available — it is a
starting hypothesis-elimination guide, not a fixed procedure.

---

## 7. Candidate Solutions

### 7.1 Remote BGE-M3 (via Hugging Face)
Call BGE-M3 through a hosted inference API instead of loading it in-process. See §8 for
verified current feasibility. Memory impact: potentially very high (removes the largest single
suspected local model). Adds network dependency and per-call latency; requires an HF token
(handled by the human, not the implementation agent — see §14/§21).

### 7.2 Smaller Local Embedding Model
Replace BGE-M3 with a smaller sentence-transformers model (e.g. a 100–400M-parameter or smaller
model) that still fits comfortably in a 512 MB budget alongside the rest of the app. Memory
impact: high, no new external dependency, but changes embedding quality/dimensionality — check
whether Chroma collection/dimension needs to be rebuilt and whether `Contract.md`'s
`ParsedDocument.chunks[].embedding_ref` shape is affected (should not be, if kept as an opaque
reference).

### 7.3 Reranker Optimization
Disable or replace the cross-encoder reranker in production mode (e.g. fall back to RRF-only
ranking, or a much smaller/reference-free reranking heuristic). Memory impact: moderate-to-high
if reranker is confirmed local and non-trivial in size; functional impact is a possible quality
reduction, but retrieval still functions via hybrid RRF alone.

### 7.4 Chroma Optimization
Lower-risk tuning: cap collection size, ensure old/duplicate demo collections are purged, or (if
measurement shows non-trivial impact) evaluate a lighter local vector index. Do not replace
Chroma preemptively — only if experiments show it is a material contributor.

### 7.5 Document Ingestion Optimization
Process/embed in smaller batches; release/`del` large intermediates (raw file bytes, full
extracted text) as soon as they're no longer needed; avoid holding all chunks' embeddings and the
full document text simultaneously if it can be streamed into Chroma incrementally. Memory impact:
moderate; no functional/contract impact; low risk.

### 7.6 Video Optimization (bounded-memory / streaming)
Ensure each visual renderer closes its resources (e.g. `plt.close(fig)` for Matplotlib) and
writes frames to temp files rather than retaining them in Python lists; feed FFmpeg from
temp-file inputs / a streaming pattern rather than batching all frames in memory first. Memory
impact: potentially high if current implementation batches; no functional impact if output video
is unchanged; moderate implementation complexity.

### 7.7 Worker/Concurrency Optimization
Reduce Uvicorn/Gunicorn worker count to 1 (or ensure heavy models are loaded once and shared, not
duplicated per worker), and/or add a concurrency guard limiting simultaneous document/video jobs
to 1 on the 512 MB instance. Memory impact: potentially very high if currently misconfigured;
very low implementation risk/complexity; should be checked first (§6) because it's nearly free to
verify.

### 7.8 Other Justified Options
- Config-driven "production/demo mode" flag (see §9) selecting among 7.1–7.7 without duplicating
  the codebase, using the existing `VectorStoreAdapter`/`LLMAdapter`/`TTSAdapter`/`AvatarAdapter`
  seams already defined in `Contract.md`.
- Lazy-loading any local model only on first actual use (rather than at startup) — reduces idle
  memory and may help isolate which requests actually trigger loading during diagnosis.

---

## 8. Hugging Face BGE-M3 Investigation

**Web-verified findings (as of this task's research; implementation agent should re-verify at
execution time since provider support can change):**

- Hugging Face offers two relevant hosted paths: **Inference Providers** (serverless, routed
  through `https://router.huggingface.co/`, billed per-token/per-request through the HF account,
  no separate provider account needed) and **dedicated Inference Endpoints** (paid, dedicated
  hardware, more setup).
- Third-party documentation (Zilliz Cloud's Hugging Face integration guide) lists **`BAAI/bge-m3`
  as a compatibility-tested Feature Extraction model returning a 1024-dimension dense vector**,
  accessed via the `hf-inference` provider route, last verified by that source in **July 2026**.
- LangChain's Hugging Face integration confirms a general pattern for calling hosted embedding
  models (`HuggingFaceEndpointEmbeddings` / `HuggingFaceInferenceEmbeddings`) via an HF API
  token, with `BAAI/bge-*` models as documented common examples (default example shown was
  `bge-base-en-v1.5`, not `bge-m3` specifically, in that particular doc).

**Confirmed:**
- BGE-M3's **dense** embedding output (1024-d) is very plausibly available via HF's hosted
  Feature Extraction / Inference Providers route, using only an HF token — no local model weights
  need to be downloaded to Render.

**NOT confirmed / requires direct verification before relying on it:**
- Whether the **sparse/lexical (SPLADE-style) output** that the current architecture diagram
  shows BGE-M3 producing (needed for the existing hybrid dense+sparse RRF retrieval) is available
  through the same hosted Feature Extraction endpoint, or only via local `FlagEmbedding`-style
  inference. Standard HF Feature Extraction endpoints typically return only the dense vector;
  sparse/multi-vector BGE-M3 outputs may require a custom-deployed Inference Endpoint or a
  different provider, not the default serverless route.
- Exact current rate limits, free-tier quota, and cold-start latency for this specific model on
  the serverless route at execution time.
- Reliability/production-suitability under hackathon judging conditions (a network hiccup mid-demo
  would surface as a user-facing failure).

**Implementation implications:**
- If only the dense vector is available remotely, the implementation agent must determine (via
  repository inspection) whether the current hybrid retrieval can gracefully degrade to
  dense-only (RRF/hybrid fusion with an empty/weighted-out sparse component) without violating
  `Contract.md`'s retrieval behavior in a way that breaks demo quality. This is a **design
  decision requiring explicit sign-off**, not something to implement unilaterally.
- If remote BGE-M3 is adopted, it must be implemented strictly behind the existing
  `VectorStoreAdapter`/embedding adapter seam so the rest of the RAG module and all downstream
  contracts are unaffected.
- The HF token itself must be treated exactly like the Gemini key: never read, printed, or
  exposed by the implementation agent (§21). Live calls to the HF API for validation are
  human-controlled, not agent-controlled.
- Moving only the embedder remote does not by itself address a potentially local reranker, or
  the video pipeline — it should be evaluated as one candidate solution among the others in §7,
  contingent on measurement confirming BGE-M3 is actually the dominant document-path contributor
  (§6).

---

## 9. Production vs Local Strategy

If measurement confirms a genuine tension between "full local quality" (useful for local
development) and "512 MB Render budget" (required for the submitted deployment), prefer a single
codebase with a **configuration/strategy switch** (e.g. an environment variable such as
`DEPLOYMENT_MODE=render` vs `local`) that selects, at the existing adapter boundaries already
defined in `Contract.md`:
- Embedding provider: local BGE-M3 (local mode) vs. remote/smaller embedder (render mode).
- Reranker: enabled (local mode) vs. disabled/lightweight (render mode).
- Document ingestion: unrestricted (local mode) vs. bounded/streaming (render mode).
- Video rendering: current implementation (local mode) vs. streaming/bounded-memory
  implementation (render mode), if measurement shows this is necessary.
- Concurrency: unrestricted (local) vs. single-job-at-a-time guard (render mode).

Do not create two parallel codebases or duplicate modules. Only introduce this switch if
measurement shows local-quality components are genuinely incompatible with 512 MB — do not
introduce it speculatively.

---

## 10. Recommended Target Architecture (conceptual — pending measurement)

```
Browser
   ↓
Existing Render URL (unchanged)
   ↓
FastAPI (single worker, or shared-model workers if measurement requires >1)
   ├── SQLite (WAL) — unchanged
   ├── Agent Orchestration (FSM) — unchanged
   ├── RAG (Lightweight/Render mode)
   │      ├── Document ingestion: streaming/bounded, releases intermediates
   │      ├── Embedding: remote (HF) OR smaller local model — per §6/§8 findings
   │      ├── Reranker: lightweight or disabled — per §6 findings
   │      └── Chroma: unchanged unless measurement shows otherwise
   ├── Gemini API (remote, unchanged)
   ├── Edge-TTS (remote, unchanged)
   └── Video pipeline (bounded-memory / streaming FFmpeg input) — per §6 findings
```
This diagram is a hypothesis of the likely end-state; it must be revised once the decision tree
in §6 produces confirmed findings. Do not implement it wholesale before that point.

---

## 11. Phase-Wise Implementation Plan

### Phase 0 — Deployment Configuration & Baseline Understanding
- **Objective**: Understand what is actually deployed today before touching code.
- **Tasks**: Inspect Procfile/`render.yaml`/start command for worker count and startup flags;
  inspect `modules/rag/src/` and `modules/avatar_voice/src/` (targeted files only, not full
  module dumps) to confirm whether BGE-M3/reranker load locally, at what point, and whether
  singleton/caching patterns exist; read `Contract.md` in full.
- **Relevant modules/files**: deployment config, `modules/rag/src/` (embedding + retrieval
  entrypoints only), `modules/avatar_voice/src/` (renderer + compositor entrypoints only),
  `instructions/Contract.md`.
- **Dependencies**: none.
- **Expected memory benefit**: none directly; this phase produces the facts needed for Phase 1–4
  to be targeted instead of speculative.
- **Risk**: none (read-only).
- **Complexity**: low.
- **Acceptance criteria**: A short written summary (in the agent's response, not a new file)
  covering: worker count, model load timing/locality for BGE-M3 and reranker, and whether video
  frames appear to be batched or streamed, each explicitly tagged as "confirmed from code" vs.
  "still unclear."
- **Static/offline validation**: code inspection only.
- **Human validation**: none required for this phase.
- **Out-of-scope**: any code change.

### Phase 1 — Lightweight Memory Instrumentation
- **Objective**: Add the minimal psutil RSS checkpoint logging identified in §5, plus 2–3
  targeted `tracemalloc` snapshots at the highest-suspicion points identified in Phase 0.
- **Tasks**: Add checkpoints per §5's list, using the log format in §12 below; reuse the existing
  `PerfTrace` instrumentor (`modules/mlops/`) if it already provides a suitable hook, rather than
  building a parallel logging mechanism.
- **Dependencies**: Phase 0 findings (to know which checkpoints matter most).
- **Expected memory benefit**: none directly (diagnostic only); negligible added overhead.
- **Risk**: low — ensure logging itself doesn't retain large objects.
- **Complexity**: low.
- **Acceptance criteria**: Checkpoints fire correctly on a local run of the topic-only and
  document-upload flows (offline/local dev, not Render) and print sane, monotonically-consistent
  RSS values.
- **Static/offline validation**: run the instrumented app locally (not on Render) with a topic-
  only request and a small local document.
- **Human validation**: none required yet.
- **Out-of-scope**: interpreting results (that's Phase 2).

### Phase 2 — Controlled Diagnostic Experiments (Human-Executed on Render)
- **Objective**: Execute Tests A–G from §5 on the actual Render deployment and collect results.
- **Tasks**: The implementation agent prepares exact step-by-step instructions and exact
  values/log lines to look for; the **human** deploys the instrumented build and runs the tests,
  reading Render's memory graph and the psutil log lines from Render logs.
- **Dependencies**: Phase 1 complete and deployed.
- **Expected memory benefit**: none directly (diagnostic only).
- **Risk**: low — instrumentation-only deploy, no functional change; still worth a quick smoke
  test that topic-only generation still works before/after adding instrumentation.
- **Complexity**: low for the agent (instructions only); execution effort is the human's.
- **Acceptance criteria**: A results table (RSS + Render memory at each checkpoint, for each
  test A–G) is available for the decision tree in §6.
- **Static/offline validation**: n/a (this phase is live-deployment by design).
- **Human validation**: primary purpose of this phase — see §17.
- **Out-of-scope**: any code change beyond instrumentation.

### Phase 3 — Fix Confirmed Document/RAG Bottleneck
- **Objective**: Implement the specific §7 candidate solution(s) that Phase 2's results point to
  for the document-upload path (e.g. §7.1/7.2 remote-or-smaller embedder, §7.3 reranker
  adjustment, §7.5 ingestion streaming, and/or §7.7 worker fix if that's the actual cause).
- **Tasks**: Implement strictly behind the `VectorStoreAdapter`/embedding adapter seam defined in
  `Contract.md`; do not touch `ParsedDocument`/`LessonPlan` contract shapes unless proven
  necessary and explicitly approved.
- **Dependencies**: Phase 2 results; if §8's sparse-vector uncertainty is relevant, get explicit
  human sign-off on the hybrid-retrieval degradation strategy before implementing.
- **Expected memory benefit**: high (this targets the confirmed dominant contributor).
- **Risk**: medium — retrieval quality could regress if reranker/embedder changes; mitigate by
  keeping local-mode as a fallback (§9) and by testing retrieval output on a few sample queries
  offline.
- **Complexity**: medium.
- **Acceptance criteria**: Document-upload lesson generation completes without OOM on Render,
  under the same demo document(s) that previously crashed; RAG grounding output remains
  meaningful (spot-checked against pre-change output offline).
- **Static/offline validation**: unit/targeted tests of the changed adapter only; no full test
  suite re-run unless directly relevant.
- **Human validation**: redeploy and re-run Test C/D on Render; confirm no crash and record new
  memory profile.
- **Out-of-scope**: video pipeline changes (Phase 4).

### Phase 4 — Fix Confirmed Video Bottleneck
- **Objective**: Implement the specific §7 candidate (typically §7.6 bounded-memory/streaming
  video generation, and/or §7.7 concurrency guard) that Phase 2's results point to for the video
  path.
- **Tasks**: Ensure renderer resource cleanup (e.g. explicit Matplotlib figure closing), switch
  frame handling to temp-file-based streaming into FFmpeg if batching is confirmed as the cause,
  and/or cap simultaneous video jobs.
- **Dependencies**: Phase 2 results.
- **Expected memory benefit**: high (targets confirmed dominant contributor).
- **Risk**: medium — output video quality/sync (audio/viseme/subtitle alignment) must not
  regress; validate against a known-good sample lesson.
- **Complexity**: medium-to-high depending on how deeply batching is embedded in current code.
- **Acceptance criteria**: Video generation for the previously-crashing demo lesson completes on
  Render without OOM; output video plays correctly with correct audio/viseme sync and duration.
- **Static/offline validation**: local render of a sample lesson, compare output video properties
  (duration, resolution, presence of audio) against a pre-change reference if available.
- **Human validation**: redeploy and re-run Test F on Render; visually confirm video output
  quality in-browser.
- **Out-of-scope**: RAG changes (already Phase 3).

### Phase 5 — Remote/Smaller Inference Strategy (Only If Not Already Covered by Phase 3)
- **Objective**: If Phase 3 did not already require it, evaluate and optionally implement the HF
  remote-BGE-M3 or smaller-local-model strategy from §7.1/7.2/§8 as a further optimization or as
  the primary mode switch described in §9.
- **Dependencies**: Phase 3 complete; explicit human sign-off on any hybrid-retrieval
  sparse-vector degradation per §8.
- **Expected memory benefit**: variable — only pursue if Phase 3's chosen fix left insufficient
  headroom (see §19 target).
- **Risk**: medium — new external dependency (HF) adds a network failure mode during live demo.
- **Complexity**: medium.
- **Acceptance criteria**: Same as Phase 3's acceptance criteria, re-verified; plus confirmed
  graceful behavior if the HF call fails (should not crash the session).
- **Static/offline validation**: mock the HF call locally; never make a live call from the agent.
- **Human validation**: human performs a live HF API test with their own token, outside agent
  execution.
- **Out-of-scope**: this phase may be skipped entirely if Phase 3 already achieves the memory
  target in §19.

### Phase 6 — Concurrency/Worker Safeguards
- **Objective**: Lock in whatever worker-count/concurrency-guard finding emerged from Phase 0/2,
  even if it wasn't the primary fix, as a safety margin against future regressions.
- **Dependencies**: Phase 0/2 findings.
- **Expected memory benefit**: low-to-high depending on Phase 0 findings; cheap insurance
  regardless.
- **Risk**: low.
- **Complexity**: low.
- **Acceptance criteria**: Deployment config explicitly documents/enforces the chosen worker
  count and any concurrency limit; a second simultaneous document/video request does not cause an
  immediate additional OOM (spot-checked, not full load-tested).
- **Static/offline validation**: config review.
- **Human validation**: brief manual two-tab test on Render if time allows (§17 Test 5).
- **Out-of-scope**: full load/stress testing (beyond hackathon scope).

### Phase 7 — Production Validation & Regression Checks
- **Objective**: Confirm the full fix set together satisfies §19's Definition of Done.
- **Tasks**: Re-run Tests A–G on the final build; confirm existing topic-only path still works
  (regression check); confirm frontend flow and API/WebSocket contracts unchanged.
- **Dependencies**: Phases 3–6 (whichever were executed) complete.
- **Expected memory benefit**: n/a (validation phase).
- **Risk**: n/a.
- **Complexity**: low.
- **Acceptance criteria**: see §19.
- **Static/offline validation**: full targeted test pass on changed modules only.
- **Human validation**: full manual pass of §17's Test 1–5 on the live Render URL.
- **Out-of-scope**: none — this is the final gate before considering the task done.

---

## 12. Priority Classification

### Critical
- Phase 0 (understand deployment) and Phase 2 (measure) — nothing else should proceed without
  these.
- Whichever of Phase 3 / Phase 4 addresses the **confirmed** dominant contributor(s).

### High
- The other of Phase 3 / Phase 4 (the second confirmed contributor, if both paths need fixes).
- Phase 6 worker/concurrency safeguard, if Phase 0 reveals a multi-worker misconfiguration (this
  can jump to Critical if confirmed, since it may be a near-zero-effort fix).

### Medium
- Phase 5 (remote/smaller embedding strategy), if Phase 3's initial fix doesn't reach the memory
  target in §19.

### Future / Deferred
- Any deeper Chroma replacement (§7.4) not shown necessary by measurement.
- Load/stress testing beyond basic concurrency safety checks.
- Any video quality/animation polish unrelated to memory.

---

## 13. Contract Preservation

Before any code change:
1. Read `instructions/Contract.md` in full.
2. Identify every contract touched by the intended fix (e.g. `ParsedDocument`,
   `TeachingSegment`, `RenderedVideoSegment`, the `VectorStoreAdapter`/`TTSAdapter`/
   `AvatarAdapter`/`LLMAdapter` interfaces).
3. Preserve existing public interfaces and JSON shapes wherever at all possible; implement
   changes behind existing adapters.
4. Do not change frontend-facing API/WebSocket payloads unless a contract change is strictly
   unavoidable — and if so, stop and log it rather than proceeding unilaterally (per
   `03_Rules.md` Absolute Rule 3).
5. Preserve module ownership boundaries from `08_Folder_Structure.md` — do not edit a module's
   `src/` outside the module(s) directly implicated by the confirmed bottleneck.
6. After any change, re-check the touched contract's consumers (e.g. if `ParsedDocument` changes,
   check `ai_agent_orchestration`'s Planner/Explainer usage) for compatibility.

---

## 14. Security Requirements

The implementation agent must, at all times:
- Never read, print, log, or transmit the contents of `.env` or any secrets file, including the
  Gemini API key or any Hugging Face token, for any reason.
- Never make a live call to Gemini, Edge-TTS, or any Hugging Face inference endpoint itself —
  all live/API validation is human-executed (see §17, §21).
- Never send repository contents to any external AI API.
- Never commit secrets or modify `.gitignore` coverage of `.env` without flagging it explicitly.
- Prefer deterministic/offline/static validation (mocked adapters, sample fixtures) at every
  phase.

---

## 15. Token-Efficient Implementation Rules

- Inspect only the files directly relevant to the current phase's confirmed or suspected
  bottleneck — do not read unrelated modules "just in case."
- Use targeted greps/searches for the specific function/class implicated (e.g. the embedding
  call site, the FFmpeg invocation) rather than dumping entire files.
- Make one logical change per step; avoid speculative refactors bundled into a bottleneck fix.
- Reuse existing utilities (e.g. the `PerfTrace` instrumentor) instead of writing parallel
  mechanisms.
- Do not introduce a new dependency unless the chosen §7 solution requires it and it's already
  on the `03_Rules.md` whitelist, or explicitly approved.
- Do not run the full repository test suite after a small, localized change — run only the tests
  covering the touched module/adapter.
- Summarize each phase's changes concisely; do not restate large chunks of code back in
  commentary.
- When live testing is required, output the exact commands for the human to run rather than
  attempting them.

---

## 16. Testing & Validation

- Offline/static: targeted unit tests for any changed adapter or renderer function; mock all
  external calls (Gemini, Edge-TTS, HF).
- Do not fabricate test results — if a test cannot be run in the current environment (e.g.
  requires FFmpeg or a GPU not available), say so explicitly rather than claiming it passed.
- Any change to a renderer or the compositor should include an offline check that output
  artifacts (image/video files) are still produced correctly on a small sample input.

---

## 17. Human Deployment Validation

The human performs these on the live Render deployment, after each relevant phase, recording
Render memory, success/failure, latency, and any logs/errors observed:

- **Test 1 — Topic-only lesson**: confirm still works (regression check) at every phase.
- **Test 2 — Small document**: the primary regression/fix-confirmation test for Phase 3.
- **Test 3 — Larger document**: confirms the fix scales, not just the smallest case.
- **Test 4 — Existing lesson → video generation**: the primary regression/fix-confirmation test
  for Phase 4.
- **Test 5 — Repeated/concurrent requests**: two near-simultaneous requests (e.g. two browser
  tabs), relevant to Phase 6; skip if time-constrained, but note it as a known residual risk if
  skipped.

The implementation agent should give the human the exact URL/flow steps and the exact Render
dashboard metric to watch for each test.

---

## 18. Rollback / Fallback Strategy

Because the existing Render URL is already submitted, every phase follows:
```
change → local/offline validation → deploy → targeted Render validation (§17)
  → compare memory & functionality against pre-change baseline → retain or rollback
```
- Each phase (3, 4, 5, 6) should be deployed and validated independently — do not bundle
  multiple risky changes into one deploy, so that a regression can be isolated to a single phase
  and rolled back (human-executed `git revert`/redeploy) without losing unrelated fixes.
- If a chosen fix (e.g. remote embedding, or reranker removal) measurably degrades RAG grounding
  quality in a way that would hurt the hackathon demo, prefer falling back to the next candidate
  in §7 (e.g. a smaller local model instead of fully remote) rather than shipping a
  memory-safe-but-low-quality result, given §32's "don't over-optimize / don't disable core
  features" principle.

---

## 19. Definition of Done

### Deployment
- Existing Render URL unchanged.
- Application starts successfully within the memory limit.
- Topic-only lesson generation remains functional (no regression).
- Document-based lesson generation completes without OOM on the tested demo document(s).
- Video generation completes without OOM on the tested demo lesson.

### Memory
- Establish a safe operational ceiling based on **measured** idle/baseline memory plus observed
  peak-during-heaviest-flow, with a genuine safety margin — do not target the full 511 MB. A
  reasonable starting point is keeping peak usage comfortably below Render's limit (e.g. with at
  least a low-double-digit percentage of headroom), but the **exact number must be derived from
  Phase 2's actual measurements**, not assumed in advance.

### Functionality
- RAG grounding remains meaningful (spot-checked, not necessarily identical to the pre-change
  implementation).
- Lesson generation, video generation, questioning, evaluation, and adaptation all remain
  functional end-to-end.
- API/WebSocket contracts and frontend flow unchanged.

### Safety
- No Gemini or Hugging Face API key exposure at any point.
- No `.env` leakage.
- No live external API calls made by the implementation agent.
- No secrets committed.
- No unauthorized `git push`/deploy actions by the implementation agent.

---

## 20. Instructions for Antigravity Implementation Agent

You are acting, phase-by-phase, as the relevant specialist:
- Phase 0/6: **Render Deployment Engineer**.
- Phase 1/2: **Senior Python/FastAPI Performance Engineer**.
- Phase 3/5: **RAG/Information Retrieval Engineer** + **ML Inference Optimization Engineer**.
- Phase 4: **Media/FFmpeg Performance Engineer**.
- Phase 7: **Render Deployment Engineer** (final validation).

Rules for every phase:
1. Understand the existing architecture (via targeted inspection, not full-repo reads) before
   changing anything.
2. Follow `08_Folder_Structure.md` module ownership and `instructions/Contract.md` exactly.
3. Preserve public contracts, the frontend, and the existing API/WebSocket behavior.
4. Make the minimal change that addresses the **confirmed** (not assumed) bottleneck for the
   current phase.
5. Work one phase at a time; stop after the phase and report findings/changes before proceeding,
   especially before Phase 3/4/5 where a design decision (e.g. §8's sparse-vector question) may
   need explicit human approval.
6. Do not perform unrelated refactoring while fixing a specific bottleneck.
7. Use only offline/static/mocked validation; never call Gemini, Edge-TTS, or Hugging Face
   endpoints directly.
8. Never read or expose `.env` or any credential.
9. Never run `git push`, `git commit`, or any other write git command — only propose exact
   commands (`git status`, `git diff`, `git add ...`, `git commit ...`) for the human to review
   and run.
10. Always distinguish, explicitly, in your reporting: measured facts vs. remaining assumptions.
11. Document the actual confirmed bottleneck(s) before proposing the corresponding fix from §7 —
    do not implement a §7 solution whose triggering hypothesis was never confirmed.
12. Give the human exact deployment/testing commands and exact Render dashboard readings to
    check for each phase's validation step.

---

## 21. Deferred Improvements

- Full load/concurrency stress testing beyond a basic two-request check.
- Chroma replacement or advanced indexing strategies, absent measurement showing necessity.
- Video visual/animation quality polish unrelated to memory.
- Avatar viseme/lip-sync realism improvements.
- Any migration off SQLite (out of scope; not implicated by the observed OOM symptoms).
- Building a dedicated Hugging Face Inference Endpoint (vs. the serverless Inference Providers
  route) unless the serverless route proves insufficient for reliability/latency.
- Broader security hardening beyond what's already noted in §14/`03_Rules.md`, since this task is
  scoped strictly to the OOM problem.
