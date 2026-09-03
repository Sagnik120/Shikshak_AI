# Issues & Architectural Decisions

This document summarizes the key architectural issues, bug fixes, and system improvements implemented across **Shikshak AI**. For comprehensive, in-depth technical postmortems with code diffs, design rationale, and test suites, see [docs/issues_faced.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/issues_faced.md).

---

## Executive Summary of Resolved Issues

| Module | Issue ID | Issue Description | Severity | Resolution Status | Verified By |
|---|---|---|:---:|:---:|---|
| **RAG** | `RAG-01` | No topic-only teaching path when `document_id=None` | **Critical (P0)** | **RESOLVED & TESTED** | `tests/integration/test_no_document_mode.py` (17/17 passed) |
| **RAG** | `RAG-02` | Latin-biased chapter detection and Indic token budget overflow | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_structure_multilingual.py` (23/23 passed) |
| **RAG** | `RAG-03` | Absence of faithfulness & anti-hallucination eval suite | **High (P1)** | **RESOLVED & TESTED** | `tests/eval/test_rag_groundedness.py` (8/8 passed) |
| **RAG** | `RAG-04` | Silent failure / missing warnings on scanned image PDFs | **Medium (P2)** | **RESOLVED & TESTED** | `ParsedDocument.warnings` diagnostic alerts |
| **RAG** | `RAG-05` | Neural reranker false rejections & threshold calibration gap | **High (P1)** | **RESOLVED & TESTED** | `tests/eval/test_reranker_recall_precision.py` (27/27 passed) |
| **RAG** | `RAG-06` | Indic subword token budgeting and trailing fragment guard | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_chunker_real_token_ground_truth.py` (23/23 passed) |
| **RAG** | `RAG-07` | Script-agnostic multilingual extraction (Bengali + Indic numerals) | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_structure_script_dispatcher.py` (38/38 passed) |
| **RAG** | `RAG-08` | Multi-domain faithfulness benchmark (Physics, Biology, CS) | **High (P1)** | **RESOLVED & TESTED** | `tests/eval/test_rag_groundedness.py` (20/20 passed) |
| **Avatar/Voice** | `AV-01` | Single static visual slides failing progressive demonstration requirements | **Critical (P0)** | **RESOLVED & TESTED** | `tests/unit/test_progressive_visuals.py` (11/11 passed) |
| **Avatar/Voice** | `AV-02` | Flat 140 WPM heuristic in offline TTS causing Hindi speech truncation | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_tts_pacing.py` (7/7 passed) |
| **Avatar/Voice** | `AV-03` | Silent FFmpeg fallback on systems without PATH binary | **High (P1)** | **RESOLVED & TESTED** | Dual-path `imageio-ffmpeg` binary resolution |
| **Avatar/Voice** | `AV-04` | Monotone delivery; cue-driven SSML prosody & Bengali voices | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_tts_cue_prosody.py` (22/22 passed) |
| **Avatar/Voice** | `AV-05` | Naive uniform visual reveal timing vs formula complexity | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_progressive_timing.py` (12/12 passed) |
| **Avatar/Voice** | `AV-06` | MuseTalk Tier-2 neural avatar architecture & transparent telemetry | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_musetalk_tier_reporting.py` (7/7 passed) |
| **Operations** | `OPS-01` | Lack of preflight diagnostic to detect runtime fallback degradation | **High (P1)** | **RESOLVED & VERIFIED** | `scripts/preflight_check.py` |
| **Operations** | `OPS-02` | CI/CD & judge preflight gap (`--require-ffmpeg`, `--check-tier2`, `--json`) | **High (P1)** | **RESOLVED & TESTED** | `tests/unit/test_preflight_enhanced.py` (8/8 passed) |

---

## Detailed Issue Tracking

For full technical descriptions, architectural analysis, code snippets, and failure mode documentation, please refer to:
- [docs/issues_faced.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/issues_faced.md)
- [modules/rag/docs/00_OVERALL_ROUND2_REVIEW.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/docs/00_OVERALL_ROUND2_REVIEW.md)
- [modules/rag/docs/rag_detail.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/docs/rag_detail.md)
- [modules/avatar_voice/docs/avatar_voice_detail.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/docs/avatar_voice_detail.md)
