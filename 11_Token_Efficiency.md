# 11_Token_Efficiency.md — Context & Token Optimization Rules

1. **Targeted reads.** Read only the instruction files relevant to the current module/task —
   do not scan the whole repo "just in case."
2. **Output compression.** Do not narrate obvious code, do not paste full duplicate files in
   chat when a diff/patch suffices.
3. **Context pressure detection.** If a session grows long and responses start losing earlier
   constraints, stop, append a `06_Memory.md` entry summarizing state, and recommend a clean
   session restart per `00_ANTIGRAVITY_START_HERE.md` "resumed session" flow.
4. **Priority rule for this project specifically**: when generating large deliverables (e.g. a
   full folder-structure ZIP) under a token budget, prioritize completing and delivering the
   artifact over exhaustive internal deliberation — finish and ship before exhausting budget.
