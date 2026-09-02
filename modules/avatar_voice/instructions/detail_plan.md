# detail_plan.md — avatar_voice

## Goal
Produce the actual "AI Teaching Video" — the PS is explicit that avatar-reads-text is NOT
sufficient; must include on-screen diagrams/equations/images/code alongside avatar+voice
(15/100 rubric points, plus 10 for voice/avatar quality/multilingual).

## Pipeline
1. **TTS**: multilingual text-to-speech from `TeachingSegment.script_text` +
   `TeachingSegment.language`, behind `TTSAdapter` (root Contract §14) so provider is swappable
   (open-source TTS for hackathon MVP; upgrade path to a premium multilingual voice API later).
2. **Avatar rendering**: talking-head/avatar video synced to the TTS audio, behind
   `AvatarAdapter`. MVP option: a simple animated avatar (viseme-driven or pre-recorded
   loop synced to audio) is acceptable to start; document clearly as MVP-tier in
   `docs/known_limitations.md` if a premium avatar API isn't available, and note the upgrade
   path.
3. **Visual synthesis** (this is the differentiator vs. "just a talking head"):
   - `equation`/`graph` → render via a math/plot library (e.g. LaTeX→image, matplotlib) from
     `visual_spec.content`.
   - `diagram` → templated SVG/diagram generation or a generative-image call with a constrained
     prompt derived from `visual_spec.content`.
   - `code` → syntax-highlighted code block + (optionally) execution-output panel for
     programming topics.
   - `timeline`/`map` → simple templated timeline/map rendering for history topics.
   - `image` → retrieved/generated illustrative image.
4. **Composition**: combine avatar video (picture-in-picture or full-frame) + the above visual
   panel + captions into one `RenderedVideoSegment` (e.g. via `ffmpeg` compositing / a headless
   browser+canvas render pipeline).
5. **Output**: store rendered segment, return `RenderedVideoSegment` (video_url, duration,
   captions_vtt_url) per Contract.

## Subject-awareness requirement
The visual chosen must genuinely match `visual_spec.type` — the harness in
`tests/eval/` (or this module's own `tests/e2e/`) should assert that e.g. a math node's rendered
video actually contains a rendered equation/graph asset, not a generic stock image.

## Performance note
Video rendering is likely the slowest step — design for asynchronous rendering with a
"lesson preparing" state surfaced to frontend (per `frontend` detail_plan) rather than blocking
the WebSocket.
