# detailed_design.md — avatar_voice Module Implementation Guide (Shikshak AI)

**Module:** `modules/avatar_voice/`
**Consumes:** `TeachingSegment` (Contract §6)
**Produces:** `RenderedVideoSegment` (Contract §7)
**Rubric weight:** 15/100 direct ("AI Teaching Video Generation") + 10/100 ("Voice & AI Avatar") + contributes to Multilingual (10)
**Status:** Implementation-ready. No Contract field renamed; additions are isolated in §9.

---

## 0. Sources this design is drawn from

| # | Source | What we take from it |
|---|--------|----------------------|
| 1 | **edge-tts** (Python package, wraps Microsoft Edge's cloud neural TTS, no API key) | Primary MVP TTS engine — <cite index="35-1">a Python module and command-line tool that gives direct access to Microsoft Edge's online text-to-speech service without needing the Edge browser, Windows, or any API key, wrapping the same cloud voices used by Edge</cite>. Also gives us <cite index="35-1">both audio output and subtitle files (SRT, VTT) in a single run</cite> and <cite index="29-1">word and sentence boundary timing events</cite> for caption sync — this directly solves the "word-level timestamp extraction" requirement without extra tooling. Community migration reports confirm it's free with effectively no rate limit, unlike quota-capped cloud APIs <cite index="33-1">Edge TTS is completely free with no API key required and no meaningful rate limits, using the same neural voices as Azure TTS</cite>.
| 2 | **Neural voice IDs** (Microsoft Edge neural voice catalog) | Exact voice short-names for the languages this project needs: <cite index="34-1">hi-IN-SwaraNeural and hi-IN-MadhurNeural for Hindi</cite>; `en-IN-NeerjaNeural` / `en-IN-PrabhatNeural` for Indian-accented English (catalog-standard names, same naming convention as the Hindi/Bengali entries confirmed in source). Voice selection is entirely config-driven, not hardcoded logic.
| 3 | **Kokoro-82M** (HF, ONNX-runtime capable, ~82M params) | Fully offline fallback TTS engine when `edge-tts`'s network call fails (edge case §5) — <cite index="28-1">a local ONNX engine among the free-by-default multi-engine TTS options, alongside edge-tts, ElevenLabs, macOS say, and espeak-ng</cite>, chosen because it needs no network and runs on CPU.
| 4 | **espeak-ng** | Last-resort, always-available offline fallback (lower quality, but zero dependency risk) — same source (#28) lists it as a basic, always-installable fallback engine, matching the "TTS network timeout" edge case requirement.
| 5 | **Wav2Lip** (Rudrabha/Wav2Lip, GitHub) | The specific lip-sync architecture we adopt for the *upgrade path* beyond MVP — <cite index="40-1">a highly accurate lip-sync model</cite> that many downstream projects (SadTalker itself) reuse as their mouth-region renderer. Chosen over full SadTalker for the upgrade path because it only needs a static/looping face video + audio, not full 3D head-pose estimation — much cheaper to run without a GPU.
| 6 | **SadTalker** (OpenTalker/SadTalker, CVPR 2023) | Reference architecture for the *stretch* full-head-motion avatar (audio→3D motion coefficients→animated head), noted as the non-MVP ceiling option. SadTalker itself internally chains a wav2lip-style module <cite index="40-1">SadTalker's checkpoints package includes wav2lip.pth as the highly accurate lip-sync model used inside its own pipeline</cite> — confirms Wav2Lip is the right lower-tier building block since SadTalker is literally built on top of it. Full SadTalker requires face-vid2vid, 3DMM extraction, and GFPGAN enhancement models — too much setup/GPU time for a hackathon MVP, hence deferred.
| 7 | **Viseme/loop-driven 2D avatar (MVP tier)** | Not from a single paper — this is the deliberately simple fallback: a small set of pre-rendered mouth-shape frames (closed / open-small / open-wide, ~3-5 visemes) swapped based on audio amplitude/energy per frame, composited onto a static illustrated avatar body. This is the documented "MVP-tier, acceptable per `detail_plan.md`" option; it needs no ML inference at all, just amplitude analysis (`librosa` RMS envelope) mapped to a small lookup table.
| 8 | **Matplotlib + LaTeX (mathtext/`usetex`)** | For `equation`/`graph` visual rendering — standard, zero-cost, deterministic; matplotlib's built-in `mathtext` renders most LaTeX-like expressions without a full TeX install, with `usetex=True` as a higher-fidelity fallback if a LaTeX distribution is present in the build environment.
| 9 | **Pygments** | For `code` visual rendering — syntax-highlighted HTML/image output, widely available, no model needed.
| 10 | **FFmpeg `filter_complex`** | For composition — industry-standard, already whitelisted in `03_Rules.md`'s dependency list, used for PiP overlay, caption burn-in, and audio-video muxing.
| 11 | **WebVTT / SRT format** | Standard subtitle formats edge-tts can emit directly (source #1), used for `captions_vtt_url` in `RenderedVideoSegment` — avoids building a custom caption format.

---

## 1. Component: TTS (`TTSAdapter`)

### Interface (per Contract §14 — exact signature, no deviation)
```python
class TTSAdapter(Protocol):
    def synthesize(self, text: str, language: str, voice_id: str) -> TTSResult: ...
```

### Internal `TTSResult` (implementation type, not a Contract schema — freely defined within this module)
```python
@dataclass
class TTSResult:
    audio_path: str          # WAV, 24kHz mono (see below)
    duration_sec: float
    word_timestamps: list[WordTimestamp]   # [{word, start_sec, end_sec}]
    vtt_path: str             # WebVTT captions
```

### Engine chain (config-driven, adapter-internal — no Contract change)
1. **Primary: `edge-tts`** (source #1). Output MP3 → transcoded to WAV 24kHz mono via `ffmpeg` (consistent input format for the avatar/lip-sync stage downstream). Word-boundary events (source #1/#29) captured during streaming and written to both `word_timestamps` and a WebVTT file.
2. **Fallback 1 (edge-tts network failure/timeout):** `Kokoro-82M` local ONNX (source #3) — same interface, runs offline.
3. **Fallback 2 (Kokoro unavailable/unsupported language):** `espeak-ng` (source #4) — always installed via apt, lowest quality but zero external dependency, guarantees the pipeline never hard-fails on audio generation.
Fallback selection logic lives entirely inside the `TTSAdapter` implementation; callers never see which engine ran — this matches the Contract's adapter-abstraction intent (§14: "swappable providers... underlying vendor can change without touching orchestration logic").

### Voice ID table (config, not hardcoded per-call)
| Language | Voice ID | Gender |
|---|---|---|
| Hindi | `hi-IN-SwaraNeural` | Female |
| Hindi | `hi-IN-MadhurNeural` | Male |
| Indian English | `en-IN-NeerjaNeural` | Female |
| Indian English | `en-IN-PrabhatNeural` | Male |
| Hinglish | `hi-IN-SwaraNeural` (edge-tts neural voices handle code-mixed text reasonably; no dedicated Hinglish voice exists) | — |
| Generic English | `en-US-AriaNeural` (source #32 confirms this as a stable, natural default) | Female |

**Assumption flagged:** no dedicated "Hinglish" voice model exists in any TTS catalog surveyed; we assume routing Hinglish text through the Hindi neural voice is acceptable for MVP (Devanagari-script TTS handles romanized/code-mixed input reasonably well in practice) rather than building a separate transliteration step. Flag for human review if voice quality is unacceptable in testing.

### Output format
WAV, 24kHz mono, 16-bit PCM — chosen as a safe, universally FFmpeg/Wav2Lip-compatible intermediate format (avoids MP3 artifacts propagating into lip-sync feature extraction).

---

## 2. Component: Avatar Rendering (`AvatarAdapter`)

### Interface (Contract §14)
```python
class AvatarAdapter(Protocol):
    def render(self, script_text: str, language: str, avatar_cue: str, audio_path: str) -> AvatarRenderResult: ...
```
Note: Contract §14 lists `AvatarAdapter.render(script_text, language, avatar_cue)`; this module's implementation additionally threads through the `audio_path` produced by the TTS step in the same call (internal wiring inside the Service Facade, §6 — not a Contract signature change, since `script_text`+`language` are what determine the audio that's already been synthesized one step earlier in the same pipeline call).

### Tier 1 — MVP (default, ships first): Viseme-loop 2D avatar
- A single static illustrated character asset (transparent-background PNG) + a small set of pre-rendered mouth-shape overlays (closed / half-open / open), source #7.
- Audio amplitude envelope extracted via `librosa.feature.rms` at 30fps granularity; RMS bucketed into 3 levels → mouth-shape frame selected per video frame.
- `avatar_cue` (`neutral|emphasis|questioning`) maps to a small set of alternate base-pose assets (e.g. slight head-tilt for "questioning", raised-eyebrow variant for "emphasis") swapped at cue boundaries — cheap, asset-based, no inference.
- Rendered as an image sequence composited by FFmpeg (not a separate video file) directly during the composition step (§4) to avoid an extra encode/decode round-trip.
- Frame rate: **24 FPS** (cinematic-standard, halves frame-generation work vs 30 FPS with negligible perceived quality loss for a talking-head PiP element).
- Transparent background maintained via RGBA PNG frame sequence, alpha-composited onto the visual panel background in the FFmpeg `overlay` filter.

### Tier 2 — Upgrade path (if time remains): Wav2Lip
- Take one static well-lit reference face image/short loop video + the WAV audio → `Wav2Lip` inference (source #5) produces a lip-synced video.
- Documented explicitly as the first upgrade increment past Tier 1, matching `detail_plan.md`'s requirement to "document clearly as MVP-tier... and note the upgrade path."
- Runs on CPU (slow, ~real-time-or-slower) or GPU if available; because Wav2Lip only needs a face crop + audio (no 3D head modeling), it's the cheapest real neural upgrade.

### Tier 3 — Stretch: SadTalker
- Full audio-driven 3D head motion (source #6) for natural head movement, not just mouth motion. Requires the multi-checkpoint model bundle (face-vid2vid, 3DMM, GFPGAN) — flagged as GPU-recommended and time-expensive to set up; only pursued if Tier 1+2 ship early and jury demo time allows a stronger visual.

**Assumption flagged:** `detail_plan.md` doesn't specify which physical avatar asset (photo/illustration) to use — assumed to be a single custom-licensed static image/short loop supplied by the team (not a real, identifiable person, to avoid any likeness/rights issue), swappable via config. Needs confirmation before asset sourcing.

---

## 3. Component: Visual Synthesis Engine

One renderer class per `visual_spec.type`, sharing a common interface:
```python
class VisualRenderer(Protocol):
    def render(self, visual_spec: dict) -> VisualRenderResult:  # {image_path | frame_sequence_dir, width, height}
```
Canvas target for all renderers: **1280×960px @ 24-bit RGBA**, matching the "70% visual viewport" region of the final 1920×1080 canvas (see §4) — rendering at that native size avoids upscaling blur.

| `visual_spec.type` | Renderer | Library/technique | Fallback on malformed content |
|---|---|---|---|
| `equation` | `EquationRenderer` | Matplotlib `mathtext` (source #8) rendering `visual_spec.content` (LaTeX string) to a transparent PNG; `usetex=True` if a TeX install is detected in the environment, else mathtext-only subset | If `content` fails to parse as LaTeX (regex/exception catch), render the raw string as plain monospace text with a small "(unformatted)" watermark rather than crashing the segment. |
| `graph` | `GraphRenderer` | Matplotlib, `visual_spec.content` expected as a small structured spec `{x, y, type: line\|bar\|scatter, labels}` (JSON-in-string per Contract's `"string\|object"` typing) | If content isn't parseable as the expected structure, fall back to `EquationRenderer`'s plain-text path. |
| `diagram` | `DiagramRenderer` | Templated SVG generation (Jinja2-templated SVG shapes: boxes/arrows/labels) from a structured `content` spec (nodes+edges) — chosen over generative image models because it's deterministic, fast, and needs no GPU/API key | If `content` isn't structured node/edge data, fall back to rendering it as a single labeled box with the raw text — never silently drop the visual. |
| `code` | `CodeRenderer` | Pygments (source #9) → syntax-highlighted image via `imgkit`/HTML-to-PNG (headless rendering, since Pygments' native output is HTML/ANSI, not an image) | If language hint missing/unrecognized, Pygments' `guess_lexer` with a plaintext-monospace fallback. |
| `timeline` | `TimelineRenderer` | Custom Matplotlib/SVG horizontal timeline template — `content` expected as ordered list of `{label, date_or_step}` | If not a list, render as a single-point timeline with the raw string as one label. |
| `map` | `MapRenderer` | Templated static SVG/PNG of a labeled region (simple coordinate-plotted markers on a base outline, not live map tiles — avoids external map-API dependency) | If coordinates absent, fall back to a text-label "map" placeholder box, matching the `diagram` fallback pattern. |
| `image` | `ImageRenderer` | Retrieval-first: an internal `image_search`-style lookup against a small curated/offline asset set is out of scope for this module's direct control (frontend/backend may own actual image sourcing) — **flagged as an open question**, see §9 | — |

**Assumption flagged:** the Contract's `visual_type` enum in `LessonPlan` (§5) lists `equation|graph|diagram|code|image|timeline|map|simulation` — this design covers all except `simulation`, which isn't detailed in `detail_plan.md`'s renderer list either. Assumed **out of scope for MVP** (would need an interactive/animated physics-style renderer, disproportionate build cost) — flagged for explicit confirmation; a `simulation` spec falls back to `DiagramRenderer`'s malformed-content path (single labeled box) until built.

Font handling: all renderers load **Noto Sans Devanagari** (bundled, open-licensed) alongside a Latin sans font for any label/caption text containing Hindi — required for correct Devanagari glyph rendering in both Matplotlib (`rcParams['font.family']`) and Pygments/PIL text layers (see §5 edge case).

---

## 4. Component: Composition Pipeline

### Canvas layout
- **1920×1080px, 16:9, 24 FPS** output.
- **Visual panel**: 70% width (≈1344×1080, left-anchored) — the rendered visual from §3, letterboxed/centered if its native aspect doesn't fill the panel.
- **Avatar PiP**: top-right, ≈30% width × ≈40% height (≈576×432), alpha-composited over a neutral panel background.
- **Caption bar**: bottom strip, ≈120px tall, semi-transparent black background, white text — captions burned in by default for MVP demo robustness (a demo video shouldn't depend on the viewer's player supporting external VTT); a **standalone WebVTT file is still generated and returned** as `captions_vtt_url` per Contract §7, satisfying both "burned-in for demo safety" and "spec-compliant separate file."

### FFmpeg `filter_complex` (representative graph)
```
ffmpeg -i avatar_frames_or_video.mov -i visual.png -i narration.wav \
 -filter_complex \
 "[1:v]scale=1344:1080:force_original_aspect_ratio=decrease,pad=1344:1080:(ow-iw)/2:(oh-ih)/2[bg]; \
  [0:v]scale=576:432[avatar]; \
  [bg][avatar]overlay=W-w-24:24[panel]; \
  [panel]drawtext=fontfile=NotoSansDevanagari.ttf:textfile=caption.txt:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-140[out]" \
 -map "[out]" -map 2:a -c:v libx264 -c:a aac -shortest output.mp4
```
(Caption text is actually driven frame-by-frame from the WebVTT timing, not a single static `drawtext` — the representative graph above is illustrative; the real pipeline burns captions via `subtitles=captions.vtt` filter for correct per-word/per-line timing instead of a single static string.)

### Audio-video drift prevention
- Total video duration is **driven by audio duration** (`-shortest` is a safety net, not the primary mechanism): the visual panel and avatar sequence are generated to *exactly* match `TTSResult.duration_sec` — visual panel simply holds its final rendered frame for any remaining time if the visual "settles" before narration ends (common for equation/diagram — render once, hold).
- If Tier-1 avatar (viseme loop) is used, its frame count is computed directly as `duration_sec * 24`, so there is no independent duration to drift — audio is authoritative.
- If Tier-2/3 (Wav2Lip/SadTalker) is used, their output is already audio-locked by construction (both models take audio as the driving signal), so no extra sync step is needed beyond a final duration sanity check (`abs(video_duration - audio_duration) < 0.1s`, else re-mux with `-shortest`/pad).

### Captions
Primary: burned-in via FFmpeg `subtitles` filter using the WebVTT produced by TTS (§1). Secondary: the same WebVTT file is uploaded/stored and its URL returned as `captions_vtt_url` — satisfies accessibility and the exact Contract field.

---

## 5. Edge Cases

- **Non-Latin script rendering (Devanagari):** every text-rendering surface (captions, code labels, diagram labels, matplotlib titles) must load `Noto Sans Devanagari` explicitly — default system/matplotlib fonts silently render Devanagari as tofu boxes. Tested via a dedicated unit test rendering a known Hindi string and checking output isn't blank/tofu (pixel-difference check against a blank-glyph reference, not OCR — cheap to implement).
- **Long/complex formulas exceeding slide boundaries:** `EquationRenderer` measures the rendered text bounding box before finalizing; if width/height exceeds the 1280×960 visual canvas, auto-shrink font size in steps (e.g. 36pt → 28pt → 20pt) until it fits, with a hard minimum of 14pt — below that, wrap into two stacked lines rather than clipping.
- **Audio duration vs. visual animation duration mismatch:** resolved structurally per §4 (audio is authoritative; visuals hold last frame or loop last state) rather than needing a runtime correction step.
- **TTS network timeout/rate limit:** engine fallback chain in §1 (edge-tts → Kokoro-82M → espeak-ng) handles this transparently; each attempt has a short timeout (e.g. 8s) before falling through, logged but not surfaced as a hard failure to the caller.
- **Async rendering / "lesson preparing" state:** video rendering is the slowest step in the whole system (TTS ~seconds, visual render ~seconds, avatar Tier-2/3 potentially tens of seconds, FFmpeg mux ~seconds) — implemented as a background job (`asyncio` task queue or a simple worker process reading from an internal queue; **not** a new Contract-level queue schema, since Contract already treats `RenderedVideoSegment` as an async-producible artifact — `video_url` implies "here once ready"). The Service Facade (§6) exposes a job-status poll internally; `backend`/`frontend` surfaces this as a "preparing" state per their own module plans, no avatar_voice Contract change needed.

---

## 6. Service Facade & Async Worker

```python
class AvatarVoiceService:
    def render_segment(self, segment: TeachingSegment) -> str:
        """
        Input: TeachingSegment (Contract §6) — node_id, script_text, language, visual_spec, avatar_cue
        Returns: job_id (internal; not a Contract type)
        Enqueues an async render job. Caller polls get_status(job_id).
        """

    def get_status(self, job_id: str) -> RenderJobStatus:
        """
        Internal type: {status: 'queued'|'rendering'|'done'|'failed', result: RenderedVideoSegment | None, error: str | None}
        """
```

Pipeline inside the worker, for one `TeachingSegment`:
1. `TTSAdapter.synthesize(script_text, language, voice_id)` → `TTSResult`
2. `VisualRenderer[visual_spec.type].render(visual_spec)` → `VisualRenderResult` (run in parallel with step 1 — independent)
3. `AvatarAdapter.render(script_text, language, avatar_cue, audio_path)` → `AvatarRenderResult`
4. Composition (§4) → MP4 + WebVTT written to object storage
5. Build and return `RenderedVideoSegment` **exactly** per Contract §7:
```python
RenderedVideoSegment = {
  "node_id": segment["node_id"],
  "video_url": "<storage url>",
  "duration_sec": <float, from TTSResult.duration_sec, video-verified>,
  "captions_vtt_url": "<storage url>"
}
```
No extra top-level keys added to this returned object — any extra internal data (which TTS/avatar engine tier was used, render time, etc.) is logged/metrics-only, never smuggled into the Contract object.

---

## 7. Testing

| Component | Test case | Expected behavior |
|---|---|---|
| TTS | Synthesize a Hindi sentence with `hi-IN-SwaraNeural` | Returns valid WAV, `duration_sec > 0`, non-empty `word_timestamps`, valid WebVTT file. |
| TTS | Force edge-tts network failure (mock) | Falls through to Kokoro-82M without raising to caller; result still valid. |
| TTS | Force both edge-tts and Kokoro unavailable | Falls through to espeak-ng; pipeline still completes (lower quality acceptable, logged). |
| Avatar (Tier 1) | 5-second audio clip | Frame count == `5 * 24 = 120`; RGBA frames non-blank; mouth-shape distribution varies with RMS envelope (not static). |
| Visual: equation | `visual_spec = {type: "equation", content: "E=mc^2"}` | Rendered PNG is non-blank, contains recognizable glyph density in the expected region (pixel-count heuristic, not OCR-perfect). |
| Visual: equation (malformed) | `content` = broken LaTeX (`\frac{1}{`) | Falls back to plain-text render, does not raise/crash the pipeline. |
| Visual: code | `visual_spec = {type: "code", content: "def f(x): return x*2"}` | Output shows syntax-highlighted (color-varied) text, not plaintext — checked via pixel color-diversity heuristic. |
| Visual: diagram | Structured node/edge JSON | Renders boxes+arrows matching node count. |
| Visual: diagram (malformed) | Plain string instead of structured JSON | Falls back to single labeled box, no crash. |
| Subject-awareness (integration) | Render a full lesson node with `visual_type: "equation"` end-to-end | Assert the resulting composed video's visual-panel region, sampled at a mid-point frame, differs meaningfully (pixel-diff) from a `visual_type: "image"` node's output — proves the equation branch didn't silently fall back to generic stock imagery. This directly implements `detail_plan.md`'s subject-awareness harness requirement. |
| Composition | Compose 5s audio + visual + avatar | Output MP4 duration within 0.1s of audio duration; captions file has entries covering the full duration. |
| Composition | Devanagari caption text | Rendered caption frame is not blank/tofu (font-load sanity check per §5). |
| Async | Enqueue 3 segments concurrently | All reach `done` status independently; no shared-state race in job status dict (use per-job locks or a proper queue, not a bare dict, in implementation). |

---

## 8. Why this approach, not alternatives

- **edge-tts over a paid multilingual TTS API for MVP:** zero cost, zero API-key setup (directly avoids `03_Rules.md`'s "Forbidden without approval: paid API requiring new billing setup"), and already gives word-level timestamps and native VTT export — removes an entire subtitle-generation subsystem we'd otherwise have to build. The `TTSAdapter` boundary keeps a premium voice API (Azure/ElevenLabs) as a pure config swap later, satisfying the PS's "upgrade path" expectation without committing hackathon time to it now.
- **Viseme-loop MVP avatar over jumping straight to Wav2Lip/SadTalker:** the PS explicitly says a talking head alone isn't sufficient and the rubric weights adaptation/RAG (35 pts) above avatar/video polish (25 pts combined) — per `01_PRD.md`'s own stated build-order implication. Spending the first build pass on a zero-inference asset-swap avatar keeps the team's time budget on the higher-weighted teaching-loop and RAG grounding work, while Wav2Lip remains a bounded, well-scoped upgrade (needs only a face image + audio, source #5) if time remains — SadTalker is deliberately deferred further since it needs a multi-checkpoint bundle (source #6) disproportionate to its marginal rubric value.
- **Deterministic template renderers (Matplotlib/SVG/Pygments) over generative-image calls for `diagram`/`equation`/`code`:** generative image APIs are slower, cost money or need a key (Rules-file friction), and are non-deterministic — bad for a live demo where an equation must reliably render as an equation (this is also exactly what the "subject-awareness validation" test in §7 checks for). Templated rendering is fast, free, and testable.
- **Burned-in captions + separate WebVTT, not WebVTT-only:** guarantees the demo video is watchable correctly in any player/recording tool (juror screen-share, video upload to submission portal) without depending on subtitle-track support, while still returning the spec-compliant `captions_vtt_url` for the frontend's own player to use natively if it wants toggle-able captions.
- **FFmpeg over a headless-browser/canvas render pipeline:** FFmpeg is already whitelisted in `03_Rules.md`, has no browser/Chromium dependency to install, and is the standard tool for this exact PiP+caption+mux composition — a headless-browser canvas approach (mentioned as an alternative in the plan) would add a heavier, slower dependency for no compositing capability FFmpeg lacks.

---

## 9. Proposed Contract Additions (NOT assumed into the design — for review only)

1. **No new fields required on `TeachingSegment` or `RenderedVideoSegment`** for the core pipeline described above — this module consumes and produces exactly the existing shapes.
2. **`image` visual type sourcing is unresolved:** `detail_plan.md` says "retrieved/generated illustrative image" but the Contract has no defined call path for `avatar_voice` to request an image (from `rag`'s corpus, a stock/curated asset set, or a generative call). **Proposed:** either (a) `avatar_voice` gets a lightweight internal curated-image lookup (out of Contract scope, purely internal), or (b) a new internal call to `rag`'s retrieval (if the lesson node has an associated document) for a "does this concept have a diagram/image already in the source material" check. This needs a decision and, if (b), a Contract-level addition analogous to `rag`'s own `RetrievalRequest`/`RetrievalResult` proposal — **not adopted here, flagged for cross-module discussion.**
3. **Optional: a lightweight async job-status field or endpoint isn't in Contract today** — this module handles it internally (§5) without requiring a Contract change, but if `backend`/`frontend` want a *standard* polling shape across modules (not just avatar_voice), that would be a `06_Memory.md`-logged cross-module proposal, not something this module should invent unilaterally.

---

## 10. Ambiguities / assumptions summary

1. **Physical avatar asset** (which image/likeness) is unspecified — assumed to be an original, non-real-person illustrated asset; needs sourcing confirmation.
2. **Hinglish voice routing** assumed to reuse the Hindi neural voice rather than a dedicated model (none exists) — flag if quality is inadequate in testing.
3. **`simulation` visual_spec.type** is in the Contract's enum but not detailed in `detail_plan.md`'s renderer list — assumed out of scope for MVP, falls back to the diagram-renderer's malformed-content path.
4. **`image` type sourcing mechanism** is unresolved and explicitly not assumed — see Proposed Contract Additions §9.2.
5. **Async job-status mechanism** implemented internally to this module only; not proposed as a new Contract-wide standard without cross-team sign-off.
