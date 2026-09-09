# contract.md — Avatar & Voice Module Specifications

This document details the interface contracts consumed, produced, and internally managed by the `avatar_voice` module.

---

## 1. Cross-Module Contracts (Root `instructions/Contract.md`)

### 1.1 Input Contract: `TeachingSegment` (Contract §6)
Consumed from `ai_agent_orchestration` during lesson execution:
```python
class TeachingSegment(BaseModel):
    node_id: str
    script_text: str
    language: Literal["en", "hi", "hinglish", "bn"] = "en"
    visual_spec: VisualSpec
    avatar_cue: Literal["neutral", "emphasis", "questioning", "encouraging", "celebratory"] = "neutral"
```

### 1.2 Output Contract: `RenderedVideoSegment` (Contract §7)
Produced for frontend playback and learning node completion:
```python
class RenderedVideoSegment(BaseModel):
    node_id: str
    video_url: str          # 1080p MP4 URL (/media/videos/... or S3/local path)
    duration_sec: float     # Total duration matching audio length
    captions_vtt_url: Optional[str] = None  # WebVTT subtitle stream URL
```

### 1.3 Pluggable Adapter Interfaces (Contract §14)
```python
class TTSAdapter(Protocol):
    def synthesize(self, text: str, language: str, voice_id: Optional[str] = None) -> TTSResult: ...

class AvatarAdapter(Protocol):
    def render(
        self,
        script_text: str,
        language: str,
        avatar_cue: str,
        audio_path: Optional[str] = None,
        duration_sec: Optional[float] = None
    ) -> AvatarRenderResult: ...
```

---

## 2. Module-Internal Data Models (`modules/avatar_voice/src/models.py`)

### 2.1 `TTSResult` & `WordTimestamp`
```python
class WordTimestamp(BaseModel):
    word: str
    start_sec: float
    end_sec: float

class TTSResult(BaseModel):
    audio_path: str
    duration_sec: float
    word_timestamps: List[WordTimestamp] = Field(default_factory=list)
    vtt_path: Optional[str] = None
    engine_used: str = "edge-tts"
```

### 2.2 `AvatarRenderResult` (Dual-Tier Support)
```python
class AvatarRenderResult(BaseModel):
    frames_dir: str
    frame_count: int
    fps: int = 24
    duration_sec: float
    is_transparent: bool = True
    tier: str = "tier1_viseme"
    tier_used: str = Field(default="tier1_viseme", description="'tier1_viseme' or 'tier2_musetalk'")
    tier_used_reason: Optional[str] = None
```

### 2.3 `VisualRenderResult` (Multi-Subject Slides)
```python
class VisualRenderResult(BaseModel):
    image_path: str
    width: int = 1344
    height: int = 1080
    visual_type: str
    step_image_paths: List[str] = Field(default_factory=list)
    step_contents: List[str] = Field(default_factory=list)
    is_progressive: bool = False
```

### 2.4 `RenderJobStatus`
```python
class RenderJobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "rendering", "done", "failed"] = "queued"
    progress_pct: float = 0.0
    stage: str = "initialized"
    result: Optional[RenderedVideoSegment] = None
    error: Optional[str] = None
```

---

## 3. Isolated Web Testbed REST Contract (Port 8004)

All testbed endpoints run on **Port 8004** to keep the production backend on Port 8000 untouched.

| Endpoint | Method | Input Payload | Response Payload |
|---|---|---|---|
| `/api/test/status` | `GET` | None | `{ status, port, tts, avatar, visuals, compositor }` |
| `/api/test/tts` | `POST` | `{ text, language, provider, avatar_cue, voice_id }` | `{ success, audio_url, vtt_url, duration_sec, word_count, timestamps, log_id, log_file }` |
| `/api/test/avatar` | `POST` | `{ script_text, language, avatar_cue, engine, audio_path }` | `{ success, tier_used, tier_used_reason, frame_count, fps, mouth_states_detected, sample_frame_urls, log_id, log_file }` |
| `/api/test/visuals` | `POST` | `{ visual_type, content, steps, execution_output }` | `{ success, visual_type, primary_image_url, step_image_urls, step_count, log_id, log_file }` |
| `/api/test/render_sync` | `POST` | `{ node_id, script_text, language, visual_spec, avatar_cue, tts_provider, avatar_engine }` | `{ success, node_id, video_url, duration_sec, captions_vtt_url, log_id, log_file }` |
| `/api/test/logs` | `GET` | Query `category`, `limit` | `{ total_logs, logs: [ { log_id, timestamp, category, operation, source_file, source_function, filename } ] }` |
| `/api/test/logs/{cat}/{fn}` | `GET` | Path params | Complete JSON manifest or formatted text log with source tracing |
