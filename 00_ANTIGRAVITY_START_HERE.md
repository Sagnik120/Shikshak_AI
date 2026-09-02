# 00_ANTIGRAVITY_START_HERE.md — Master Session Bootstrap Prompt

## Purpose
Paste this file's content as the FIRST message to any coding agent (fresh session) working on the
**AI Teacher — Human-Like AI Educator (AI Innovation Hackathon 2026, Round 2)** project.

## Reading Order (fresh session)
1. `00_ANTIGRAVITY_START_HERE.md` (this file)
2. `01_PRD.md`
3. `02_Architecture.md`
4. `03_Rules.md`
5. `08_Folder_Structure.md`
6. `04_Phases.md`
7. Your assigned module's `instructions/overview.md`
8. Your assigned module's `instructions/detail_plan.md`
9. `instructions/Contract.md` (root) — READ FULLY before writing any function signature
10. `06_Memory.md` — read last 3 entries only

## Reading Order (resumed session)
1. `06_Memory.md` (latest entries)
2. `09_Progress_Tracker.md` / `docs/progress.md`
3. Your module's `instructions/detail_plan.md`
4. `instructions/Contract.md` — re-verify nothing changed

## Operational Guardrails
- The AI agent NEVER runs destructive terminal commands (`rm -rf`, force-push, drop DB) without explicit human approval.
- The AI agent NEVER reads, prints, or exfiltrates `.env` or any secret file, under any framing.
- Only the human executes: deployments, secret rotation, billing-related API calls.
- Repository boundary: an agent assigned to a module (e.g. `modules/rag/`) may read root docs but must NOT edit files inside another module's folder without a Contract change request.
- **STOP-AND-WAIT**: before generating any code, the agent must restate (a) which module, (b) which contract(s) apply, (c) exit criteria for the task, and wait for human confirmation.

## Adapting This Template
Define your own `START_HERE.md` per hackathon/project by setting: primary entry prompt, the doc read sequence, and session-recovery rules (this file already does that for this project).
