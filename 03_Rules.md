# 03_Rules.md — Hard AI Agent Rules & Boundaries

## Absolute Rules
1. NEVER execute destructive actions (delete data, force-push, drop tables, revoke keys)
   without explicit human approval in-session.
2. NEVER read, print, log, or transmit the contents of `.env` or any secrets file — not even
   to "verify configuration." If a task seems to require it, STOP and ask a human.
3. NEVER silently change the architecture defined in `02_Architecture.md` or a module's
   `Contract.md` entry. Propose the change, log it in `06_Memory.md`, wait for approval.
4. NEVER delete or overwrite working, tested code without explicit approval — prefer additive
   changes or clearly-flagged refactors.
5. NEVER fabricate results (e.g. claiming a test passed when it did not run).

## Stop-and-Ask Conditions
Stop and request human guidance when:
- A change requires touching more than one module's contract simultaneously.
- A new third-party dependency/library is needed that isn't in the whitelist below.
- An error persists after 2 focused debugging attempts and the root cause is unclear.
- The task would require credentials, billing, or external account setup.
- The requested behavior conflicts with `01_PRD.md` non-goals.

## Tooling & Dependency Whitelist (proposed — extend via Contract negotiation)
**Allowed:** FastAPI, Pydantic, React/Next.js, Tailwind, LangChain/LlamaIndex, Chroma/Qdrant,
HuggingFace `transformers`/`sentence-transformers`, `pytest`/`vitest`, `ffmpeg`, standard TTS
libraries, PDF/DOCX/PPTX parsing libs (`pypdf`, `python-docx`, `python-pptx`).
**Forbidden without approval:** any paid API requiring a new billing setup, any library that
telemetry-phones-home by default, any GPL-incompatible dependency if the project license
requires permissive licensing (confirm license stance in `06_Memory.md`).

## Secret Handling
- All secrets live in `.env` (never committed — verify `.gitignore` covers it).
- Code reads secrets via environment variables only; never hardcode.

## Terminal Command Execution
- The AI agent may run: install, lint, test, build commands.
- Only the human runs: deploy, publish, `git push` to shared/protected branches, and anything
  touching billing or external credentials.
