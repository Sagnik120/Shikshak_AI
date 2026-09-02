# 00B_SPEC_UPGRADES.md — Iteration & Hardening Protocol

## Purpose
Governs how the system evolves from MVP (Task 1 + Task 2 mandatory requirements) into
Stage 2/3 hardened, production-grade behavior (see `new_phases.md` for the upgrade backlog).

## Rules
1. **One spec at a time.** Never implement two upgrade specs from `new_phases.md` in parallel inside the same module.
2. **No unwritten specs.** If a technique/paper is not documented in the module's `detail_plan.md` or an approved upgrade spec, the agent must NOT implement it — propose it in `06_Memory.md` and stop.
3. **Touches whitelist.** Every upgrade spec must declare exactly which files/folders it is allowed to modify. Anything outside that list is out of bounds without a new Contract negotiation.
4. **No silent architecture changes.** Swapping a mock (e.g. mock TTS) for a real service (e.g. real TTS API) requires updating `instructions/Contract.md` for that module AND flagging any dependent module.
5. **Backward compatibility.** Upgrades must not break a module's published Contract without a version bump (`v1` → `v2`) and a migration note in `06_Memory.md`.

## When to Use
- Moving Task 1 (teaching video) MVP → adding real diarized multilingual TTS.
- Moving heuristic misconception detection → trained/prompted misconception classifier.
- Moving in-memory learner profile → persistent DB-backed profile store.
