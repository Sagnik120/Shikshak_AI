# Phase 1 — Grounded, Full-Length, Structured Lesson Loop + Visible Assessment

## Role
Act as a senior full-stack AI engineer specializing in RAG-grounded agentic educational systems and rapid hackathon MVP implementation (Python/FastAPI/WebSocket + Vanilla JS frontend).

## Objective
Make the existing Shikshak AI pipeline visibly grounded in the uploaded document, produce teaching videos of the planned length, show structured chapter notes, and surface the Assessment report — with the smallest safe patches. **Time box: 60–75 min.** If a task exceeds its estimate by 15 min, log it in `06_Memory.md`, skip, continue.

## Context (from provided docs + screenshots; verify in code)
- Pipeline: RAG → Planner → Explainer(+visual) → Avatar/Voice → Questioner → ML Core eval → Adaptation → Assessment. Contracts in `instructions/Contract.md` are authoritative. Frontend is Vanilla JS/HTML (`index.html`, `classroom.html`, `report.html`, `classroom.js`, `api.js` per docs).
- Observed: upload card says "RAG Indexed (0 sections)" and shows hardcoded **biology** chips under a Newton PDF; AI Inspector "Grounding Evidence" stays "Waiting for RAG retrieval…"; 3-node plan for a 15-min "Newton's Laws" request; script ≈90 words ⇒ video 0:38; script shown as one paragraph; checkpoint card visible while video at 0:01; no assessment report visible.

## Repository Instructions
Inspect actual code before editing; do not trust this file's assumptions over the repo. Follow `Contract.md`, `10_Git_Discipline.md`, `11_Token_Efficiency.md`, relevant module docs and `03_Rules.md`. Log decisions/CCRs in `06_Memory.md` (≤10 lines).

## Hard Rules
1. Inspect before editing; 2. don't blindly follow assumptions here; 3. preserve `Contract.md`; 4. minimal changes; 5. no architecture rewrite; 6. no new dependencies; 7. no agent logic duplicated in frontend; 8. no RAG logic duplicated in Planner (use the existing RAG service); 9. no Assessment logic duplicated in frontend; 10. **never call Gemini or any external AI API**; 11. **never open/read/print/modify `.env`**; 12. **no git commands** (leave changes uncommitted); 13. no long-running commands; 14. no unrelated refactors; 15. keep the existing demo working. Don't fabricate test results — if something needs a live LLM/TTS run, write `HUMAN LIVE TEST REQUIRED`.

## Step 0 — Read-only Investigation (≤10 min) → short findings report (≤25 lines)
Answer, with file/function names you actually find:
1. **RAG/Planner:** How does an uploaded doc's `document_id` reach the live session and Planner? Is retrieval called for planning? Are chunks (text + `chunk_id`/`section_title`/`page_or_slide`) placed in the Planner prompt? What does "(0 sections)" derive from? What does retrieval return for weak/no context (`risk_level`)?
2. **Citations:** Is there already a citation/provenance carrier from Explainer/backend to the frontend (the `citation-source-text` element and Grounding Evidence panel)? What fields does it get?
3. **Explainer:** Where is `est_minutes` used? Explainer prompt length instructions? `max_output_tokens`, truncation, JSON-repair, or slicing of `script_text` anywhere between Explainer → backend → Avatar/Voice? Does the Planner's `est_minutes` sum ≈ time budget?
4. **Visual spec:** What visual_type/`visual_spec.content` did a physics node get, and which renderer consumed it? (Just report; fixes for rendering are Phase 2.)
5. **Assessment:** Where is lesson end detected in the FSM? Is AssessmentAgent invoked? Is `final_report` (or equivalent) emitted over WS? What does `classroom.js`/`report.html`/`api.js` do with it (mock?). How is `score_pct` computed?
6. **Frontend:** what populates the chips under the uploaded file; what triggers the checkpoint card display.

Proceed immediately with all work that needs no contract change. **Ask the human once (single message) for approval only when you reach the task needing it:**
- **CCR-1:** optional `TeachingSegment.notes = {key_points: string[3–5], example: string|null}` (produced in the same Explainer LLM call).
- **CCR-2 (only if Q2 finds no carrier):** optional `TeachingSegment.citations = [{chunk_id, source_name, page_or_slide|null, section_title|null, snippet≤200 chars}]`, populated by the system from retrieval metadata — never by the LLM.
If not approved, implement the fallback only.

## Tasks (execution order)

### 1.A RAG → Planner grounding + visible provenance (P0, ~25 min)
- Ensure that when a document is attached, the RAG service retrieves (query = topic + constraints) and top chunks are passed to Planner with their metadata; if not, fix the wiring (reuse existing RAG service).
- Planner prompt: when excerpts are present, "derive lesson nodes and examples only from the provided excerpts; do not invent content not supported by them"; topic-only mode unchanged.
- Explainer (per node) must also receive retrieved chunks for that node's concept (verify existing behavior; fix only if missing).
- Provenance = system-generated from retrieval metadata of chunks actually placed in the prompt, filtered by the **existing** citation threshold. Never let the LLM author citation IDs. Reuse the existing carrier; else CCR-2.
- Populate the **Grounding Evidence** panel: file name + page/section + short snippet + grounding risk badge for the current node; before first node show "Grounded in: <file> (N chunks)". Weak/no context: "No matching document context — using general knowledge" and **no** citation.
- Log (server, no secrets): `document_id`, chunk count, top rerank scores, chunk_ids passed to Planner.
- Fix "(0 sections)": show real chunk/section count or hide the count when unknown.

### 1.B Explainer edit — length, speech-safe script, visual_spec sanity, optional notes (P0, ~15–20 min; ONE prompt/schema edit)
- Add a single named constant for speaking rate (~140 wpm; observed ≈90 words → 38 s) and teach share (0.7). `target_words = clamp(est_minutes × 0.7 × 140, 100, 600)`. Inject into the Explainer prompt as a required range (target ±25 %) and structure: hook → explanation → analogy/example → recap. Respect learner level/language/style.
- `script_text` must be speech-only: no markdown/headings/LaTeX; formulas spoken in words. LaTeX belongs only in `visual_spec`.
- Remove/raise any cap, slicing or truncation found in Q3; check `max_output_tokens` is sufficient for the target size; ensure the **full** script reaches Avatar/Voice.
- Log per node: `script_words`, `target_words`; frontend/backend log the rendered `duration_sec`. Optional single "expand" retry **only** if an existing retry/repair path makes it trivial; otherwise skip.
- If Planner's `est_minutes` don't sum to ≈ time budget (teaching+checkpoint), fix in Planner prompt/post-processing minimally.
- visual_spec sanity: ensure prompt/validation produces content matching the chosen visual_type for the topic (no placeholder/sample labels). Deep renderer fixes are Phase 2.
- If CCR-1 approved: also request `notes {key_points, example}` in the same JSON; rules: only restate facts present in the script; no new facts. Make it optional in Pydantic; the SmartMock adapter must still return schema-valid output.

### 1.C Structured chapter notes UI (P1, ~15 min)
- Replace the below-video paragraph with a "Chapter Notes" card for the current node: concept heading, depth + est_minutes chips, formula (KaTeX, from `visual_spec` when type is equation; try/catch fallback to plain text), **Key points** (`notes.key_points` if present, else first 3–4 sentences of the script as bullets), **Example** (`notes.example` if present, else omit), and a collapsed `<details>` "Full transcript" with the script.
- Notes tab: accumulate notes per completed node; finish with **Key Takeaways** (first 1–2 key points per node). Empty state: neutral loading text, no placeholder content.
- Frontend renders only data it receives; no LLM/RAG logic in JS.

### 1.D Assessment surfaced (P0, ~15 min)
- Trace and fix each hop: lesson end (last node resolved, incl. HUMAN escalation) → AssessmentAgent → persistence → WS `final_report` (or existing name) → frontend handler → render.
- Render (in a modal/section or via `report.html` loaded with **real** report data, not `api.js` mocks): `score_pct`, `strong_areas`, `weak_areas`, `recommended_next`, `narrative_feedback`. Empty lists → "None identified yet". Contract field names only.
- `score_pct` must derive from `EvaluationResult` history (e.g., `partial_credit`), not LLM invention; if the agent lets the LLM invent it, override deterministically. If the LLM/narrative fails, fall back to deterministic text (SmartMock path) without crashing.
- Add a visible "View learning report" call-to-action at lesson end.

### 1.E Small UI defects (P1, ~10 min)
- Remove hardcoded biology chips under uploaded file: show top 3–5 `detected_structure.key_terms` from the upload response if available, else hide.
- Checkpoint gating: show the checkpoint card only after the video `ended` (or the video is seeked to the end) — verify first; if already gated, skip. Disable "Check my answer" after submit until the response arrives (per status doc).

## Safe Checks (Antigravity)
Python compile/import checks on touched modules; `node --check` on touched JS; existing offline tests **only** after confirming they use the mock/SmartMock adapter and never construct the live Gemini adapter; optional small offline test with stub retrieval + prompt-recording stub LLM proving (a) doc chunks appear in the Planner prompt, (b) target word range appears in the Explainer prompt, (c) `final_report` payload matches `AssessmentReport`. Validate Pydantic schemas still accept old payloads (optional fields). Everything requiring live Gemini/TTS → `HUMAN LIVE TEST REQUIRED`.

## Human Browser Verification (`http://localhost:8000/`; 5 min, Beginner, English, Visual & Analogy; note 3 canary terms from the PDF first)
| # | Do | Expect | Failure |
|---|---|---|---|
| H1 | Upload Newton PDF, generate plan, open AI Inspector | Nodes reflect PDF concepts; canary appears in plan/script; Grounding Evidence shows file+page/section+snippet+risk badge | Stuck on "Waiting for RAG retrieval…"; generic plan |
| H1b | Repeat without upload | "no document context"; no citations | Citations appear |
| H2 | Watch segments | Total teaching ≈3–4 min; each segment ≈ `est_minutes×0.7` ±30 %; check server log words vs target | Any segment <~40 s |
| H3 | Look under video + Notes tab | Structured heading/chips/formula/key points/example; transcript collapsed; Key Takeaways | One big paragraph, raw LaTeX |
| H4 | Answer checkpoints (one wrong, then right); finish lesson | Report shows score_pct, strong/weak areas, next steps, narrative | No report / mock data |
| H5 | Reload index page; play video | No biology chips; checkpoint appears after video ends | Old chips; card visible at 0:01 |
| H6 | 3 consecutive wrong answers; free-text answer | MODIFY→REGENERATE→HUMAN; text submits | Regression |

## Definition of Done
All P0 tasks wired and safe-checked; CCR outcomes logged; no contract-breaking changes; final message (≤15 lines): what changed (module-level), any CCR used, what needs `HUMAN LIVE TEST REQUIRED`, and known leftovers.
