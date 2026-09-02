# 08_Folder_Structure.md — Canonical Repository Layout

```
Shikshak_AI/
├── 00_ANTIGRAVITY_START_HERE.md
├── 00B_SPEC_UPGRADES.md
├── 01_PRD.md
├── 02_Architecture.md
├── 03_Rules.md
├── 04_Phases.md
├── 05_Design.md
├── 06_Memory.md
├── 07_Test.md
├── 08_Folder_Structure.md
├── 09_Progress_Tracker.md
├── 10_Git_Discipline.md
├── 11_Token_Efficiency.md
├── new_phases.md
├── instructions/                  # ROOT-level, cross-module instructions
│   ├── Contract.md                 # <-- single source of truth for all inter-module contracts
│   └── Overview.md                 # <-- whole-system overview for any agent/LLM to onboard fast
├── tests/                          # ROOT-level cross-module tests
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── eval/
│   ├── smoke/
│   └── fixtures/
├── docs/                           # submission documentation deliverables
│   ├── architecture.md
│   ├── models_and_apis_used.md
│   ├── rag_implementation.md
│   ├── personalization_approach.md
│   ├── assessment_methodology.md
│   ├── multilingual_implementation.md
│   ├── voice_and_avatar.md
│   ├── setup_instructions.md
│   ├── deployment_instructions.md
│   ├── known_limitations.md
│   └── progress.md                 # generated/maintained per 09_Progress_Tracker.md
├── scripts/                        # helper scripts (setup, run_all_diagnostics wrapper, seed data)
└── modules/
    ├── frontend/
    │   ├── instructions/
    │   │   ├── overview.md
    │   │   ├── detail_plan.md
    │   │   └── contract.md
    │   ├── tests/
    │   │   ├── unit/
    │   │   ├── integration/
    │   │   └── e2e/
    │   └── src/                    # (empty — code added during Phase 0+)
    ├── backend/                     (same instructions/ + tests/ + src/ pattern)
    ├── ml_core/                     (same pattern)
    ├── ai_agent_orchestration/      (same pattern)
    ├── rag/                         (same pattern)
    ├── avatar_voice/                (same pattern)
    ├── mlops/                       (same pattern)
    └── testing/                     (owns cross-module harness config; same pattern)
```

## Ownership Principle
Each module folder is single-responsibility and independently developable once
`instructions/Contract.md` is agreed. No module's `src/` may be edited by an agent not
assigned to that module without a Contract change request logged in `06_Memory.md`.
