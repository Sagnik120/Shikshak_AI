# MLOps Module — Comprehensive Architectural & Technical Detail

> **Module Identifier**: `mlops`  
> **Repository Path**: `modules/mlops/`  
> **Primary Role**: Service Orchestration, Model/Adapter Registry, Caching, Observability & Token/Cost Accounting  
> **Status**: **SCAFFOLDED & CONTRACT-LOCKED** (Adapter interfaces defined in Contract §14)  
> **Key Contracts**: Contract §14 (`Adapter Interfaces: LLMAdapter, TTSAdapter, AvatarAdapter, VectorStoreAdapter`), Observability Schema

---

## 1. The Task (In Simple Language)

Imagine the backstage crew, sound engineers, and stage managers of a major theatrical production:
1. **Keeping the lights and power on**: Ensures that all the complex machinery (databases, AI models, video encoders) starts up with a single button press so the actors (the AI Teacher) can perform seamlessly.
2. **Swapping tools behind the scenes**: If a microphone breaks, the sound engineer swaps it for a backup microphone instantly without interrupting the show. (In Shikshak AI, if an external AI service is down, MLOps swaps to a backup provider without changing a single line of teaching code).
3. **Tracking expenses and timing**: Measures how much electricity, money, and time each scene takes so the production never runs out of budget or stalls on stage.
4. **Caching rehearsed scenes**: If a scene has already been recorded perfectly, MLOps pulls it from the archive rather than spending time and money re-recording it from scratch.

The **`mlops`** module is this backstage engineering crew for Shikshak AI. It manages containerization, adapter registries for swappable AI models, structured logging for the live audit feed, multimedia caching, and latency/cost monitoring.

---

## 2. Technical Details & Architecture

The MLOps subsystem provides the operational foundation that keeps Shikshak AI resilient, fast, and observable:

### Adapter Registry Pattern (Contract §14)
Every external AI service is decoupled behind a clean, swappable abstract interface:
- **`LLMAdapter`**: Wraps OpenAI, Anthropic, Google Gemini, or local Ollama models.
- **`TTSAdapter`**: Wraps Microsoft Edge-TTS, ElevenLabs, or offline acoustic fallbacks.
- **`AvatarAdapter`**: Wraps Viseme 2D procedural rendering, Wav2Lip, or third-party cloud avatar APIs.
- **`VectorStoreAdapter`**: Wraps local ChromaDB, Qdrant, or Pinecone.

Provider selection is 100% environment-variable driven (e.g. `LLM_PROVIDER=gemini` or `TTS_PROVIDER=edge_tts`), allowing the system to run in pure offline mode or high-fidelity cloud mode without any code changes.

### Multi-Tier Caching System
- **Embedding Cache**: Hashes document chunk text via SHA-256 to avoid re-embedding identical text across sessions.
- **Segment Video Cache**: Hashes the tuple `(node_id, hash(script_text), language, avatar_cue)`. If a video segment has already been rendered, `AvatarVoiceService` returns the cached MP4 instantly, reducing demo latency to near-zero.

### Structured Observability & Audit Trail
Every transition in the teaching state machine is logged as a structured JSON event:
```json
{
  "timestamp": "2026-09-04T02:00:00Z",
  "session_id": "sess_123",
  "stage": "ADAPTING",
  "node_id": "node_02",
  "decision": "MODIFY",
  "reason": "Misconception detected: confused force with velocity",
  "llm_tokens": 420,
  "latency_ms": 850
}
```
These logs are simultaneously streamed to the frontend right-panel audit log and persisted for debugging.

### Session Cost & Resource Tracker
Calculates real-time computational cost per session:
$$\text{Total Cost} = (\text{Tokens}_{\text{in}} \times P_{\text{in}}) + (\text{Tokens}_{\text{out}} \times P_{\text{out}}) + (\text{TTS Chars} \times P_{\text{tts}}) + (\text{Video Secs} \times P_{\text{render}})$$
Provides judges and developers with full visibility into production economics.

---

## 3. What is Implemented Till Now (Current Status)

| Subsystem | Specification & Status | Status |
|---|---|---|
| **Contract §14 Interfaces**| Abstract adapter interfaces defined in `instructions/Contract.md` (§14). | **Contract-Locked & Verified** |
| **TTS & Avatar Adapters** | Concrete implementations of `TTSAdapter` and `AvatarAdapter` built and verified in `modules/avatar_voice/`. | **Complete** |
| **Vector Store Adapter** | Concrete implementation of `VectorStoreAdapter` built and verified in `modules/rag/`. | **Complete** |
| **Module Specifications** | `instructions/overview.md`, `instructions/detail_plan.md`, `instructions/contract.md` defining caching schemes and telemetry. | **Complete** |
| **Directory Skeleton** | `src/` and `tests/` (`unit/`, `integration/`, `e2e/`) partitioned and prepared. | **Scaffolded** |
| **Docker Compose & Telemetry**| Orchestration compose file and metrics aggregator ready for deployment sprint. | **Next Immediate Sprint** |

---

## 4. Full File Structure

```
modules/mlops/
├── docs/
│   └── mlops_detail.md                         # This authoritative documentation file
├── instructions/
│   ├── contract.md                             # Authoritative cross-module contract definitions
│   ├── detail_plan.md                          # Telemetry, caching, and registry specifications
│   └── overview.md                             # High-level module mission statement
├── src/
│   ├── .gitkeep                                # Active source directory
│   ├── __init__.py                             # (Target architecture) Package exports
│   ├── adapters/                               # (Target architecture)
│   │   ├── __init__.py                         # Provider factory & registry
│   │   ├── avatar_registry.py                  # Dynamic AvatarAdapter provider selector
│   │   ├── llm_registry.py                     # Dynamic LLMAdapter provider selector
│   │   ├── tts_registry.py                     # Dynamic TTSAdapter provider selector
│   │   └── vector_registry.py                  # Dynamic VectorStoreAdapter provider selector
│   ├── caching/                                # (Target architecture)
│   │   ├── __init__.py                         # Exposes CacheManager
│   │   ├── embedding_cache.py                  # SHA-256 persistent embedding vector cache
│   │   └── video_cache.py                      # Segment video cache keyed by script & cue hash
│   ├── metrics/                                # (Target architecture)
│   │   ├── cost_tracker.py                     # Per-session token and multimedia cost calculator
│   │   └── latency_logger.py                   # Stage execution duration profiler
│   └── service.py                              # (Target architecture) MLOpsService unified facade
└── tests/
    ├── e2e/
    │   └── .gitkeep                            # Cache hit-rate and provider failover tests
    ├── integration/
    │   └── .gitkeep                            # Integration tests with adapters
    └── unit/
        └── .gitkeep                            # Registry resolution and cost tracker unit tests
```

---

## 5. Detailed File Logic (Planned & Authoritative Architecture)

### Target Files in `src/`
- **`src/adapters/` (Provider Registries)**:
  - `llm_registry.py`: Reads `LLM_PROVIDER` environment variable. Returns initialized instance of `OpenAIAdapter`, `GeminiAdapter`, or `OllamaAdapter`.
  - `tts_registry.py`: Reads `TTS_PROVIDER`. Returns `EdgeTTSAdapter` or `FallbackTTSAdapter`.
  - `vector_registry.py`: Reads `VECTOR_STORE_PROVIDER`. Returns `ChromaVectorStoreAdapter` or cloud alternatives.
- **`src/caching/video_cache.py`**:
  - `VideoCache`: Generates a deterministic key:
    `cache_key = sha256(f"{node_id}_{hash(script_text)}_{language}_{avatar_cue}".encode()).hexdigest()`
  - Checks if `cache/{cache_key}.mp4` exists on disk. If so, skips synthesis and returns the existing path immediately.
- **`src/metrics/cost_tracker.py`**:
  - `CostTracker`: Accumulates token usage from LLM API responses and character counts from TTS requests. Computes total estimated cost in USD/INR.
- **`src/metrics/latency_logger.py`**:
  - Profiling decorator measuring latency across each pipeline step (`ingest`, `plan`, `synthesize_tts`, `render_avatar`, `compose_video`).

---

## 6. How the Module Works (Execution Flow & Runtime Lifecycle)

```
[Application Startup]
         |
         v
[MLOps reads environment configuration: LLM_PROVIDER, TTS_PROVIDER, etc.]
         |
         v
[Instantiates registered Adapters behind Contract §14 interfaces]
         |
======================= RUNTIME PIPELINE =======================
         |
         +---> [Stage Triggered: e.g. Video Rendering Request]
         |          |
         |          v
         |     [video_cache.py: Check cache key hash]
         |          |
         |     +----+--------------------------------+
         |     | Cache HIT                           | Cache MISS
         |     v                                     v
         |  Returns cached MP4 immediately      Dispatches to AvatarVoiceService
         |  (Latency: < 10ms)                        |
         |                                           v
         |                                      Saves new MP4 to cache/
         |
         +---> [Observability & Telemetry]
                    |
                    v
               [latency_logger.py] Records step duration
               [cost_tracker.py] Increments tokens & compute cost
                    |
                    v
               Structured Log Event emitted to WebSocket / UI
```

---

## 7. Cross-Module Connections & Contract Integration

| Direction | Connected Module | Contract Reference | Protocol / Data Shape |
|---|---|---|---|
| **Across All Modules** | `rag`, `ai_agent_orchestration`, `avatar_voice` | **Contract §14** (`Adapter Interfaces`) | Supplies concrete adapter instances based on configuration. |
| **Inbound** | `ai_agent_orchestration` | **Contract §11** | Captures state machine transitions for structured audit logging. |
| **Inbound** | `avatar_voice` | **Contract §6, §7** | Intercepts render calls for video segment caching. |
| **Outbound** | `frontend` (via Backend WS) | Observability Feed | Streams formatted JSON audit logs to the right-panel thought feed. |

---

## 8. Full System Overview (Module-Wise Context)

In the complete 8-stage Shikshak AI teaching loop:
`Understand -> Plan -> Explain -> Demonstrate -> Question -> Evaluate -> Adapt -> Continue`

The **`mlops`** module operates as the cross-cutting foundation supporting every single stage:
- Provides reliable models for **Understand, Plan, Explain, and Evaluate**.
- Accelerates **Demonstrate** via video caching.
- Logs every decision in **Adapt & Continue** to prove the system's human-like intelligence to hackathon judges.

---

## 9. Critical Notes for Any LLM Agent Working on This Module

> [!IMPORTANT]
> **Strict Guardrails for LLM Agents:**
> 1. **Zero Hardcoded Vendors**: Never instantiate a vendor client (e.g. `openai.OpenAI()` or `chromadb.Client()`) directly inside business logic. Always route through the adapter registry in `modules/mlops/src/adapters/`.
> 2. **Cache Invalidation Safety**: Video caching keys must incorporate `avatar_cue` and `language`. An explanation in English with `avatar_cue="emphasis"` must never return a cached Hindi segment or a `neutral` gesture segment.
> 3. **Keep Hackathon Scope Lean**: Do not build complex Kubernetes Helm charts or distributed service meshes. A rock-solid `docker-compose.yml` and local disk cache are 100% sufficient and optimal for demo day.
