# Shikshak AI (शिक्षक AI)
### Autonomous, Multimodal, Human-Like AI Educator
> **AI Innovation Hackathon 2026 (Round 2)** | *AI Teacher Track*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![RAG](https://img.shields.io/badge/RAG-BGE--M3%20%2B%20ChromaDB-orange.svg)](https://github.com/FlagOpen/FlagEmbedding)
[![Audio--Visual](https://img.shields.io/badge/Avatar-24%20FPS%20Visemes%20%2B%20FFmpeg-purple.svg)](#avatar--voice-synthesis)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)

---

## 📖 Executive Summary

**Shikshak AI** is an autonomous AI educator that transforms static educational documents into interactive, personalized, broadcast-grade teaching experiences. Rather than simply reading text aloud, Shikshak AI:
1. **Understands & Grounds**: Parses multilingual documents (PDF, DOCX, PPTX, TXT) across English, Hindi, and Bengali using **BGE-M3** hybrid retrieval and cross-encoder reranking.
2. **Orchestrates Pedagogically**: Runs a 7-state finite state machine (`IDLE` ➔ `PLAN` ➔ `TEACH` ➔ `INTERACT` ➔ `EVALUATE` ➔ `ADAPT` ➔ `ASSESS`) driven by 5 specialized LLM agents (Planner, Explainer, Questioner, Evaluator, Assessor).
3. **Visualizes Dynamically**: Synthesizes neural voices (Edge-TTS) with 24 FPS lip-synced visemes composited alongside dynamic visual boards (LaTeX equations, 2D/3D graphs, code execution panes) via FFmpeg.
4. **Detects & Adapts**: Evaluates student responses in real time, diagnoses root misconceptions, and dynamically adapts teaching analogies and pacing before proceeding.

---

## 🏛️ System Architecture

```
                                  ┌────────────────────────┐
                                  │   Learner Web UI       │
                                  │ (Canvas + Telemetry)   │
                                  └───────────┬────────────┘
                                              │ Full-Duplex WebSocket
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             BACKEND SERVICE (FastAPI)                            │
│ ┌──────────────────────┐  ┌───────────────────────┐  ┌─────────────────────────┐ │
│ │ Auth & Session Store │  │ WebSocket Dispatcher  │  │ Dependency Container    │ │
│ └──────────────────────┘  └───────────────────────┘  └────────────┬────────────┘ │
└───────────────────────────────────────────────────────────────────┼──────────────┘
                                                                    │
                 ┌──────────────────────────────────────────────────┼────────────────────────────────┐
                 ▼                                                  ▼                                ▼
┌─────────────────────────────────┐               ┌───────────────────────────────────┐ ┌────────────────────────────────┐
│      RAG RETRIEVAL ENGINE       │               │      TEACHER ORCHESTRATOR         │ │    AVATAR & VOICE SYNTHESIS    │
│  • Multi-format Parsers         │ ──Context──▶  │  • 7-State Pedagogical FSM        │ │  • Neural Edge-TTS + SSML      │
│  • Devanagari & Bengali NLP     │               │  • Planner & Explainer Agents     │ │  • 24 FPS Viseme Engine        │
│  • BGE-M3 Dense + Sparse        │               │  • Questioner & Assessor Agents   │ │  • 6 Dynamic Visual Renderers  │
│  • RRF + Cross-Encoder Rerank   │               │  • Gemini 2.0 Flash / SmartMock   │ │  • FFmpeg 1080p Compositor     │
└─────────────────────────────────┘               └─────────────────┬─────────────────┘ └────────────────────────────────┘
                                                                    │
                                                                    ▼
                                                  ┌───────────────────────────────────┐
                                                  │          ML CORE ENGINE           │
                                                  │  • Semantic Overlap & Rule Match  │
                                                  │  • Misconception Taxonomy Matcher │
                                                  │  • Dynamic Pedagogy Adapter       │
                                                  └───────────────────────────────────┘
```

---

## 📂 Repository Organization

All cross-module communication is governed strictly by [`instructions/Contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md).

```
Shikshak_AI/
├── README.md                          # Primary project landing page & quickstart
├── instructions/                      # Inter-module contract & onboarding
│   ├── Contract.md                    # Canonical cross-module schema contract (v1.0.0)
│   └── Overview.md                    # System-level architecture onboarding
│
├── docs/                              # Consolidated documentation library
│   ├── README.md                      # Documentation index & map
│   ├── spec/                          # Hackathon specs, PRDs, rules (00_* through 11_*)
│   └── system/                        # Operational guides, audits, test progress, setup
│
├── modules/                           # Subsystem source code, docs, & tests
│   ├── rag/                           # Document parsing, chunking, indexing, retrieval
│   ├── avatar_voice/                  # TTS synthesis, viseme generation, visual rendering
│   ├── ai_agent_orchestration/        # 5-agent pedagogical FSM & prompt templates
│   ├── ml_core/                       # Scoring, misconception diagnosis, adaptation
│   ├── backend/                       # FastAPI server, WebSocket streams, container DI
│   ├── frontend/                      # Interactive student client & telemetry HUD
│   ├── mlops/                         # Telemetry, logging, metrics instrumentation
│   └── testing/                       # Cross-module test harnesses & assertion suites
│
├── tests/                             # Root-level test suites (unit, integration, eval, smoke)
└── scripts/                           # Preflight checks, diagnostics, and seed scripts
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.10+ (macOS, Linux, or WSL)
- `ffmpeg` (installed and accessible on `PATH`)
- Optional: `tesseract` (for image/scanned PDF OCR)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Sagnik120/Shikshak_AI.git
cd Shikshak_AI

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Verify System Health (Preflight Check)
Run the automated environment and hardware capability diagnostic:
```bash
python scripts/preflight_check.py
```

### 4. Configure API Keys (Optional)
Create a `.env` file in the root directory:
```env
# Optional: Set Gemini API key for live LLM reasoning (falls back to SmartMock deterministically if unset)
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 5. Launch the Server
```bash
# Start the FastAPI backend server on port 8000
python -m uvicorn modules.backend.src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Access the Learner Web Interface
Open your browser and navigate to:
```
http://localhost:8000/
```
*(Or open [`modules/frontend/src/index.html`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/frontend/src/index.html) in your browser)*

---

## 🧪 Testing & Validation

Execute automated test suites across all tiers:

```bash
# Smoke tests (fast verification of critical paths)
pytest tests/smoke/ -v

# Unit tests (isolated component verification)
pytest tests/unit/ -v

# Cross-module integration tests
pytest tests/integration/ -v

# Groundedness and pedagogical evaluation rubrics
pytest tests/eval/ -v

# Run entire suite
pytest tests/
```

---

## 📚 Documentation Links

- 🧭 **[Documentation Hub](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/README.md)** — Complete map of all specifications and guides.
- 📐 **[Inter-Module Contract](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md)** — Canonical schema definitions.
- 🔬 **[Technical Audit Brief](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/technical_audit.md)** — Real vs. mocked code breakdown.
- 🛠️ **[Issues & Postmortems](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/issues_faced.md)** — In-depth architectural problem-solving records.
- 🚀 **[Setup Commands Reference](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/setup_commands.md)** — Detailed environment setup guide.
