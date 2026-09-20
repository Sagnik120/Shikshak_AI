# Phase 2 — Visual & Avatar Presentation Polish

## Role
Act as a senior full-stack AI engineer with strong Python imaging/FFmpeg and frontend presentation skills, focused on rapid hackathon MVP polish within the existing Avatar/Voice pipeline.

## Objective
Make teaching videos look educational and credible: topic-relevant boards, readable typography, no raw LaTeX, cleaner avatar presentation — **presentation only, no contract changes, no pipeline redesign.** **Time box: 40–45 min.** Start only after Phase 1 is done and human-verified.

## Context (provided docs + screenshots; verify in code)
- Avatar/Voice has: Edge-TTS, 24 FPS transparent viseme avatar (`AvatarAdapter`), 6 visual renderers (LaTeX equation, 2D plot, 3D surface, code, flowchart, takeaway cards), FFmpeg 1080p compositor (≈70 % board, ≈30 % top-right avatar PiP, burned-in subtitles).
- Observed in the classroom video: a physics (inertia) node rendered a generic flowchart labelled "Input Data → Processing Engine → Adaptive Reasoning → Estimated Output" (unrelated placeholder-like content); nodes tiny and occupying ~half the board; header strip with illegible tiny text; cartoon avatar; a light-blue rounded square with a blue dot overlapping the avatar PiP corner; users also report raw LaTeX at times.
- Design tokens (05_Design): bg `#0B1220`, panel `#111A2E`, alt `#1A2540`, border `#26324A`, text `#F5F7FA`/`#A9B4C7`, cyan `#4FD1E8`, gold `#E3A63E`.

## Repository Instructions
Inspect actual code before editing. Follow `Contract.md`, `10_Git_Discipline.md`, `11_Token_Efficiency.md`, `03_Rules.md`, module docs.

## Hard Rules
Same 15 rules as Phase 1: inspect first; preserve contracts; minimal patches; no rewrites/new dependencies; no duplicated agent/RAG/assessment logic in frontend; **no Gemini/external AI calls; no `.env` access; no git commands**; no long-running commands; no unrelated refactors. Do not run full renders that call Edge-TTS/Gemini — test renderer functions locally and mark `HUMAN LIVE TEST REQUIRED` for full video.

## Tasks

### 2.A Board relevance + fallback (P1, ~10 min)
Find why the physics node got the generic flowchart *(hypotheses — verify, don't assume)*: (i) `simulation`/unsupported `visual_type` falls to a default renderer; (ii) `visual_spec.content` doesn't match the renderer's schema so built-in sample labels render; (iii) Explainer emitted generic content.
- Map every allowed `visual_type` (`equation|graph|diagram|code|image|timeline|map|simulation`) to one of the existing renderers deliberately: physics laws/`simulation` → equation card (+ takeaway card if no formula); `image`/`map`/`timeline` → takeaway or flowchart only when real content exists.
- Renderers must **never** render built-in sample labels. On invalid/missing content, fall back to a **title + concept takeaway card** built from `node concept`/`script` first sentences (always topically right) and log a WARNING naming the fallback.

### 2.B Legibility & hierarchy (P1, ~15 min)
At 1920×1080 canvas: board title bar with the node concept (≥44 px); body/bullets ≥34 px; flowchart node labels ≥28 px with word-wrap and nodes scaled to fill the board area; equation centered ≥96 px; code ≥26 px monospace, wrapped/limited lines; ≤4 bullets per takeaway card; generous padding; palette from the tokens above with one accent; high contrast; remove the tiny illegible header strip (or make it a readable subtitle). Prioritize equation, takeaway, flowchart; touch others only if trivial.

### 2.C LaTeX sanitizer + fallback (P1, ~10 min)
Add one input sanitizer for equation content before rendering: strip `$`, `$$`, `\(...\)`, `\[...\]`, markdown code fences and "latex:" prefixes; collapse JSON double-escaping (`\\frac` → `\frac`); trim. Try the existing renderer; on parse failure, render a **plain/Unicode fallback** (small map e.g. `\Sigma→Σ`, `\vec{F}→F⃗`, `\cdot→·`, `\times→×`, `\frac{a}{b}→a/b`, `_`/`^` simplified) — a backslash sequence must never be displayed. Frontend KaTeX usages must wrap in try/catch with the same plain fallback. Add a tiny offline test (renderer function only) with ~8 samples: `F = ma`, `\sum F = 0`, `\frac{\Delta v}{\Delta t}`, `\vec{F}_{net}=0`, double-escaped, `$$…$$`-wrapped, and an invalid string.

### 2.D Avatar presentation using existing capabilities (P1/P2, ~15 min)
- Inspect avatar assets/adapters/tiers/config: if a better tier/asset already exists and is selectable, make it default. **Photorealistic avatars are out of scope** (paid API forbidden without approval; GPU models infeasible) — keep `AvatarAdapter` swap point untouched.
- Composition: larger, bottom-anchored bust in the PiP; rounded corners, thin `#26324A`/cyan border, soft panel background, small "Shikshak" label; keep PiP away from subtitles.
- Identify the source of the blue-circle badge on the avatar corner (video frame vs HTML overlay); remove if it is a leftover placeholder.
- Lip-sync: smooth viseme selection (minimum hold ~2 frames; closed mouth in silence). Optional (only if ≤10 min): subtle idle bob (±2 px) or blink via existing frame variants.

### 2.E Stretch (only if ≥15 min remain; else skip)
Notes-panel and report-page styling consistent with tokens; if compositor supports it trivially, switch board (equation → takeaway) at segment midpoint for long segments. Otherwise defer.

## Safe Checks (Antigravity)
Compile/import checks; `node --check`; offline LaTeX-sanitizer test; render a single **local-only** static board image (no TTS/network) for each of equation/takeaway/flowchart to a temp path and inspect visually for size/overflow; existing offline renderer tests if they don't touch network/Gemini. Delete temp files afterwards.

## Human Browser Verification (5-min lesson on Newton's Laws; also try one biology/other topic)
| # | Do | Expect | Failure |
|---|---|---|---|
| V1 | Watch a physics node | Topic-relevant board (equation/takeaway), no "Input Data/Processing Engine" labels | Generic flowchart |
| V2 | Look at board at fullscreen | Title bar + readable text; no tiny text; layout uses full board | Text unreadable, empty half-board |
| V3 | Node with a formula | Formula readable, no backslashes/`$` shown; also in Notes | Raw LaTeX |
| V4 | Watch avatar | Cleaner framed PiP; no stray blue badge; mouth closes in silences | Badge still present, jittery mouth |
| V5 | Regression: full lesson to report | Video plays, checkpoint, adaptation, report all still work | Any Phase 1 feature broken |

## Definition of Done
Boards never show placeholder content; LaTeX never leaks; avatar presentation visibly improved; no contract or pipeline changes; final message (≤10 lines): changes, fallbacks added, items marked `HUMAN LIVE TEST REQUIRED`, deferred items.
