# 10_Git_Discipline.md — Version Control & Commit Protocol

## Commit Granularity
One logical change per commit (one task, one test script, one contract update). No monolithic
"implement everything" commits.

## Conventional Commits Format
```
<type>(<scope>): <description>
```
Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`.
Scope: module name, e.g. `feat(rag): add pdf chunker`, `test(ai_agent_orchestration): add
adaptation-controller edge cases`.

## Agent Git Commands
- Before committing, the agent outputs the exact `git add`/`git commit` commands for human review
  (or executes them only if pre-approved for that session).
- Agent must check `.gitignore` covers `.env`, `node_modules/`, model weights/checkpoints, and
  rendered video output directories before first commit.
