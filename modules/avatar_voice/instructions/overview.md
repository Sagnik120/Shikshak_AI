# overview.md — Avatar & Voice Module Overview

## 1. What This Module Does
The `avatar_voice` module produces the complete multimodal **AI Teaching Video** for Shikshak AI. It transforms pedagogically structured lesson segments (`TeachingSegment`) into broadcast-quality 1080p MP4 educational videos (`RenderedVideoSegment`) combining:
1. **Multilingual Neural Speech (TTS):** Natural Indian-accented English, Hindi, Hinglish, and Bengali narration with pedagogical prosody (SSML cue shifts) and word-level WebVTT timestamps.
2. **Dual-Tier Lip-Sync Avatar:** Tier 2 MuseTalk neural diffusion with automatic fallback to Tier 1 procedural 24 FPS transparent visemes with RMS-driven mouth shapes and natural blink cycles.
3. **Multi-Subject Visual Engine:** 7 specialized subject-aware slide generators (LaTeX equations, syntax-highlighted code, function plots, node flowcharts, historical timelines, geography maps, diagrams) with step-by-step progressive reveal derivations.
4. **1080p FFmpeg Video Compositor:** Synchronizes a 70% left visual slide (1344x1080) and a 30% right avatar stream (576x1080) with burned-in dynamic captions.
5. **Asynchronous & Synchronous Service:** Non-blocking job queue with progressive percentage updates alongside immediate synchronous rendering.
6. **Isolated Web Testbed on Port 8004:** Dedicated studio with light professional UI and hierarchical logging to test every module and trace errors down to the exact `.py` file and function.
7. **Real Production Engines (Zero Mocks):** Operates on real Microsoft Edge Neural Cloud TTS, real 24 FPS RGBA viseme frames, real Matplotlib LaTeX/Pygments rendering, and real bundled FFmpeg binary (v7.1), backed by automated multi-tier failovers guaranteeing zero crashes in production.

---

## 2. Directory Structure
```
modules/avatar_voice/
├── instructions/                       # Module specifications & plans
│   ├── overview.md                     # This file
│   ├── detail_plan.md                  # Milestone progress, testbed & logging specs
│   ├── contract.md                     # Interface schemas & REST endpoint contracts
│   └── detailed_design_avatar_voice.md # Comprehensive engineering design
├── docs/
│   └── avatar_voice_detail.md          # 27 source files analysis & logic breakdown
├── src/
│   ├── tts/                            # EdgeTTS, Fallback Pure Python, Resilient Factory
│   ├── avatar/                         # VisemeAdapter, MuseTalkAdapter, AvatarFactory
│   ├── visuals/                        # 7 renderers (equation, code, graph, diagram, etc.)
│   ├── compositor/                     # FFmpeg 1080p split-screen video muxer
│   ├── models.py                       # Pydantic schemas (TTSResult, VisualSpec, etc.)
│   └── service.py                      # AvatarVoiceService (sync & async queue)
└── tests/
    ├── unit/                           # Isolated unit tests (21 tests)
    ├── eval/                           # Subject awareness & edge-case evaluations (7 tests)
    ├── integration/                    # Full pipeline composition tests (2 tests)
    └── web_test/                       # Isolated Web Testbed Studio on Port 8004
        ├── server.py                   # Standalone FastAPI server (Port 8004)
        ├── logger.py                   # Hierarchical AvatarVoiceTestLogger engine
        ├── logs/                       # Categorized log subdirectories (tts, avatar, visuals, etc.)
        └── static/                     # Light professional UI (HTML, CSS, JS)
```

---

## 3. Reading Sequence
1. [overview.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/instructions/overview.md) (This overview)
2. [contract.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/instructions/contract.md) (Input/Output data contracts and testbed API)
3. [detail_plan.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/instructions/detail_plan.md) (Milestones, testbed implementation, logging specs)
4. [avatar_voice_detail.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/docs/avatar_voice_detail.md) (Deep dive into all 27 Python source files and internal logic)
5. [detailed_design_avatar_voice.md](file:///Users/sagnikchandra/Documents/Hackathon/Bharat_Academix/Shikshak_AI/modules/avatar_voice/instructions/detailed_design_avatar_voice.md) (Comprehensive design rationale)
