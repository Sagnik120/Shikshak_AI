# overview.md — backend

## Mission Statement
The `backend` module serves as the central API gateway, session orchestration coordinator, and persistent state manager for Shikshak AI. It acts as the operational nervous system connecting the student-facing frontend application to all underlying AI microservices (`ai_agent_orchestration`, `rag`, `ml_core`, `avatar_voice`), maintaining server-authoritative state across the entire 8-stage interactive teaching lifecycle.

---

## Core Capabilities
1. **Dual-Protocol Communication Gateway**: High-throughput FastAPI REST API surface alongside full-duplex, bidirectional WebSocket relay channels.
2. **Server-Authoritative Session Lifecycle**: Tracks and persists state transitions (`CREATED -> INGESTING -> PLANNED -> EXPLAINING -> AWAITING_ANSWER -> EVALUATING -> ADAPTING -> ASSESSING -> COMPLETE`) ensuring mid-lesson disconnects resume seamlessly.
3. **Decoupled Microservice Container**: Interacts exclusively with other modules via contract-defined interfaces (`RAGService`, `AvatarVoiceService`, `TeacherOrchestrator`, `MLCoreService`), avoiding direct LLM or vector DB dependencies.
4. **Pluggable Persistence Layer**: Fast in-memory repositories for sessions, documents, learner profiles, and assessment reports, with disk-backed binary storage adapters.
5. **Dedicated Web Testbed Studio**: Standalone FastAPI diagnostic service on **Port 8005** with an elegant, modern light professional UI and hierarchical execution logging.

---

## Directory Map
```
modules/backend/
├── docs/
│   └── backend_detail.md                  # Comprehensive architectural and technical specification
├── instructions/
│   ├── contract.md                        # Cross-module contract bindings (§1–13) and testbed REST schemas
│   ├── detail_plan.md                     # Implementation plan, components, and testbed details
│   ├── overview.md                        # High-level mission and directory map
│   ├── task_backend_src.md                # Source engineering task specifications
│   └── task_backend_testing.md            # Testing strategy and integration scenarios
├── src/
│   ├── api/
│   │   ├── rest.py                        # REST route handlers (/sessions, /upload, /topic, /plan)
│   │   └── ws.py                          # WebSocket relay handler (/sessions/{id}/live)
│   ├── auth.py                            # Session token generation and validation
│   ├── config.py                          # Settings and CORS configuration
│   ├── integrations/
│   │   └── container.py                   # Service container bridging all microservices
│   ├── main.py                            # Production FastAPI application entrypoint (Port 8000)
│   ├── persistence/
│   │   ├── base.py                        # Abstract repository base classes
│   │   ├── in_memory.py                   # Concrete in-memory repositories
│   │   └── storage.py                     # Filesystem binary storage adapter
│   ├── schemas/
│   │   ├── contract.py                    # Contract-conforming Pydantic models
│   │   └── ws.py                          # WSMessage framing schema
│   └── state/
│       └── driver.py                      # SessionDriver orchestrating TeacherState
└── tests/
    ├── e2e/                               # End-to-end user journey tests
    ├── e2e_mocked/                        # Mocked journey tests
    ├── integration/                       # Microservice boundary tests
    ├── unit/                              # Pytest unit tests (sessions, auth, persistence)
    └── web_test/                          # Standalone diagnostic testbed (Port 8005)
        ├── logger.py                      # Hierarchical logging engine
        ├── server.py                      # FastAPI testbed application
        ├── logs/                          # Categorized test trace logs
        └── static/                        # Light professional diagnostic UI
```

---

## Required Readings
1. Root `instructions/Contract.md` (specifically Contract §1, §2, §3, §5, §6, §8, §9, §10, §11, §12, §13)
2. Root `02_Architecture.md`
3. Module `instructions/detail_plan.md`
4. Module `docs/backend_detail.md`
