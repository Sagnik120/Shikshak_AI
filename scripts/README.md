# `scripts/` — Developer & Operational Tooling

This directory contains standalone CLI scripts and utilities for environment setup, model provisioning, preflight health-checks, diagnostic verification, and live terminal demonstrations.

> **Note**: Automated unit, integration, and regression suites live under `tests/` and `modules/*/tests/` (run via `pytest`). The scripts here are executable command-line applications designed for operators, developers, and hackathon judges.

---

## Script Index & Usage Reference

| Script | Purpose | Usage Command | When to Use |
| :--- | :--- | :--- | :--- |
| **[`setup_env.sh`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/scripts/setup_env.sh)** | Creates `.venv`, updates pip, installs all dependencies, and runs preflight verification in one command. | `bash scripts/setup_env.sh` | Initial repo setup on a fresh machine. |
| **[`setup_and_download_models.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/scripts/setup_and_download_models.py)** | Verifies directory layout and pre-downloads the BGE-M3 model weights (~2 GB) for offline readiness. | `python scripts/setup_and_download_models.py` | Before running offline demos or testing without internet. |
| **[`preflight_check.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/scripts/preflight_check.py)** | Comprehensive system health check: verifies FFmpeg, Edge-TTS, ChromaDB, Indic NLP, and model availability. | `python scripts/preflight_check.py` | Before every demo, judging presentation, or deployment. |
| **[`run_live_demo.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/scripts/run_live_demo.py)** | Runs an end-to-end interactive terminal lesson with real lesson planning, video segment generation, question checkpoints, and adaptive feedback. | `python scripts/run_live_demo.py` | To demonstrate the complete teaching loop from the command line. |
| **[`verify_live_gemini_quality.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/scripts/verify_live_gemini_quality.py)** | Tests live Gemini 2.0 Flash reasoning quality across Planner, Explainer, and Questioner agents using your `GEMINI_API_KEY`. | `python scripts/verify_live_gemini_quality.py` | When verifying Gemini API connectivity and schema validation. |
| **[`run_rag_diagnostics.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/scripts/run_rag_diagnostics.py)** | Runs standalone verification on RAG parsing, token chunking, and vector retrieval with per-test millisecond timings. | `python scripts/run_rag_diagnostics.py` | When testing or profiling RAG retrieval latency and parsing. |
| **[`run_avatar_voice_diagnostics.py`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/scripts/run_avatar_voice_diagnostics.py)** | Runs standalone verification on TTS voices, 24 FPS visemes, and FFmpeg video compositing with latency logs. | `python scripts/run_avatar_voice_diagnostics.py` | When testing audio synthesis, voice catalogs, or video rendering. |

