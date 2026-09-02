# 05_Design.md — Visual & UI/UX Design System

> Colors/patterns below are extracted from the reference screenshot provided (Bharat Academix
> site) — reused here purely as the visual language for OUR app's UI shell, not its content.

## Layout Blueprint
- **Left panel**: Input — upload dropzone / topic input, learner constraints form
  (level, language, time budget, style).
- **Center panel**: Lesson stage — video player (teaching video) transitioning into interactive
  question cards during checkpoints; a compact "lesson map" progress strip above it.
- **Right panel**: Decision & audit log — live view of teacher-agent stage
  (Understand/Plan/Explain/.../Adapt), current `AdaptationDecision`, and running assessment
  score. (Mirrors the "audit log" panel pattern from the architecture template.)

## Color Tokens (dark theme, from reference)
```
--bg-primary:      #0B1220   /* near-black navy background */
--bg-panel:        #111A2E   /* card/panel surface */
--bg-panel-alt:    #1A2540   /* secondary card surface */
--border-subtle:   #26324A
--text-primary:    #F5F7FA
--text-secondary:  #A9B4C7
--accent-cyan:     #4FD1E8   /* primary CTA (e.g. "WhatsApp Us Now" pill) */
--accent-gold:     #E3A63E   /* highlight / badges */
--status-green:    #3FCF8E   /* correct / understood */
--status-yellow:   #E3C23E   /* partially understood */
--status-orange:   #E38A3E   /* struggling */
--status-red:      #E35D5D   /* incorrect / misconception flagged */
```

## Typography
- UI headings/body: system sans-serif (e.g. Inter).
- Telemetry / agent-state / audit log panel: monospace (e.g. JetBrains Mono) to visually
  distinguish "machine reasoning" from "lesson content."

## UI States
- Lesson video: loading → playing → paused-for-question → resuming.
- Interaction card: unanswered → submitted → correct (green) / partial (yellow) / incorrect (red)
  with inline re-explanation reveal.
- Agent-state chip in right panel updates live: `PLANNING`, `EXPLAINING`, `QUESTIONING`,
  `EVALUATING`, `ADAPTING`.

## Non-Goals
Do not invest in animation polish, marketing-site chrome, or theming options until the teaching
loop (Phases 0–7) is functionally complete — visual fidelity is 5/100 rubric points, adaptation
is 20/100.
