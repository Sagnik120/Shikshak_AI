# 08_Folder_Structure.md — Canonical Repository Layout

```
Shikshak_AI/
├── README.md                          # Primary project landing page, quickstart & docs index
├── instructions/                      # ROOT-level, cross-module instructions
│   ├── Contract.md                    # <-- single source of truth for all inter-module contracts
│   └── Overview.md                    # <-- whole-system overview for any agent/LLM to onboard fast
├── docs/                              # Consolidated documentation library
│   ├── README.md                      # Documentation index and map
│   ├── spec/                          # Hackathon specifications, rules, blueprints (00_* through 11_*)
│   └── system/                        # Operational guides, audits, test progress, setup
├── tests/                             # ROOT-level cross-module tests
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── eval/
│   ├── smoke/
│   └── fixtures/
├── scripts/                           # Helper scripts (preflight, diagnostics, seed data)
└── modules/
    ├── frontend/
    │   ├── docs/ (frontend_design.md, frontend_detail.md, ideas.md)
    │   ├── instructions/ (overview.md, detail_plan.md, contract.md)
    │   ├── tests/
    │   └── src/
    ├── backend/                       (docs/ + instructions/ + tests/ + src/)
    ├── ml_core/                       (docs/ + instructions/ + tests/ + src/)
    ├── ai_agent_orchestration/        (docs/ + instructions/ + src/prompts/ + src/)
    ├── rag/                           (docs/ + instructions/ + tests/ + src/)
    ├── avatar_voice/                  (docs/ + instructions/ + tests/ + src/)
    ├── mlops/                         (docs/ + instructions/ + src/)
    └── testing/                       (docs/ + instructions/ + tests/)
```

## Ownership Principle
Each module folder is single-responsibility and independently developable once
`instructions/Contract.md` is agreed. No module's `src/` may be edited by an agent not
assigned to that module without a Contract change request logged in `06_Memory.md`.
