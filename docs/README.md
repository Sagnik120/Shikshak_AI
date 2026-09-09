# Shikshak AI — Documentation Hub

Welcome to the central documentation library for **Shikshak AI (शिक्षक AI)**, an autonomous, multi-agent AI educator combining grounded RAG, 24 FPS lip-synced audio-visual avatars, active learning loops, and dynamic pedagogy adaptation.

---

## Quick Navigation

| Section | Description | Key Links |
| :--- | :--- | :--- |
| **[Specifications & Rules](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec)** | Hackathon PRD, architectural blueprint, agent bootstrap, and rules | [`00_ANTIGRAVITY_START_HERE.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/00_ANTIGRAVITY_START_HERE.md), [`01_PRD.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/01_PRD.md), [`02_Architecture.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/02_Architecture.md) |
| **[System & Operations](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system)** | Technical audit, architectural postmortems, and repository structure | [`technical_audit.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/technical_audit.md), [`issues_faced.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/issues_faced.md) |
| **[Inter-Module Contract](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md)** | Canonical Pydantic schemas and interface boundaries (v1.0.0) | [`instructions/Contract.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/instructions/Contract.md) |

---

## 1. Specifications & Blueprints (`docs/spec/`)
- [`00_ANTIGRAVITY_START_HERE.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/00_ANTIGRAVITY_START_HERE.md) — Master bootstrap prompt and reading order for AI coding agents.
- [`00B_SPEC_UPGRADES.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/00B_SPEC_UPGRADES.md) — Spec upgrades, rubrics, and high-priority requirements.
- [`01_PRD.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/01_PRD.md) — Product requirements document, user personas, and target outcomes.
- [`02_Architecture.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/02_Architecture.md) — High-level system architecture, data flows, and subsystem boundaries.
- [`03_Rules.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/03_Rules.md) — Engineering constraints, forbidden patterns, and dependency whitelists.
- [`04_Phases.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/04_Phases.md) — Sequential implementation and verification phases (Milestones 1 & 2).
- [`05_Design.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/05_Design.md) — UX, visual design tokens, and avatar presentation aesthetics.
- [`06_Memory.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/06_Memory.md) — Architectural decision log and session continuity memory.
- [`07_Test.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/07_Test.md) — Test pyramid strategy (unit, integration, e2e, smoke, eval).
- [`08_Folder_Structure.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/08_Folder_Structure.md) — Canonical folder organization and ownership principles.
- [`09_Progress_Tracker.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/09_Progress_Tracker.md) — Project milestones, checklist items, and deliverables.
- [`10_Git_Discipline.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/10_Git_Discipline.md) — Commit standards, branch conventions, and clean history rules.
- [`11_Token_Efficiency.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/spec/11_Token_Efficiency.md) — Guidelines for conserving LLM context and optimizing prompt payloads.

---

## 2. System Operations & Diagnostics (`docs/system/`)
- [`technical_audit.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/technical_audit.md) — Literal code-level audit distinguishing 100% production algorithms from test doubles.
- [`issues_faced.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/issues_faced.md) — In-depth postmortems of technical hurdles and root-cause solutions.
- [`repo_summary.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/docs/system/repo_summary.md) — Concise structural summary of packages, contracts, and scripts.

---

## 3. Subsystem Implementation Deep-Dives

Detailed technical guides for each module's architecture:

- **RAG & Knowledge Grounding**:
  - Implementation Guide: [`modules/rag/docs/rag_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/docs/rag_detail.md)
  - Detailed Design: [`modules/rag/instructions/detailed_design.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/rag/instructions/detailed_design.md)
- **Avatar & Voice Synthesis**:
  - Implementation Guide: [`modules/avatar_voice/docs/avatar_voice_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/docs/avatar_voice_detail.md)
  - Detailed Design: [`modules/avatar_voice/instructions/detailed_design_avatar_voice.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/instructions/detailed_design_avatar_voice.md)
- **AI Agent Orchestration**:
  - Implementation Guide: [`modules/ai_agent_orchestration/docs/ai_agent_orchestration_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ai_agent_orchestration/docs/ai_agent_orchestration_detail.md)
- **Backend & FastAPIs**:
  - Implementation Guide: [`modules/backend/docs/backend_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/backend/docs/backend_detail.md)
- **ML Core & Assessment**:
  - Implementation Guide: [`modules/ml_core/docs/ml_core_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/ml_core/docs/ml_core_detail.md)
- **Frontend & UI**:
  - Design Specs: [`modules/frontend/docs/frontend_design.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/frontend/docs/frontend_design.md)
  - Implementation Guide: [`modules/frontend/docs/frontend_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/frontend/docs/frontend_detail.md)
  - Creative Philosophy: [`modules/frontend/docs/ideas.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/frontend/docs/ideas.md)
- **MLOps & Pipeline**:
  - Implementation Guide: [`modules/mlops/docs/mlops_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/mlops/docs/mlops_detail.md)
- **Testing & Test Harness**:
  - Implementation Guide: [`modules/testing/docs/testing_detail.md`](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/testing/docs/testing_detail.md)
