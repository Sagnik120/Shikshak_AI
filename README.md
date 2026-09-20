# Shikshak AI (शिक्षक AI)

### An autonomous, multimodal AI educator that adapts when you get stuck

> **AI Innovation Hackathon 2026 (Round 2)** · *AI Teacher Track*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57.svg)](https://www.sqlite.org/)
[![RAG](https://img.shields.io/badge/RAG-BGE--M3%20%2B%20ChromaDB-orange.svg)](https://github.com/FlagOpen/FlagEmbedding)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#)

---

## What it does

Shikshak AI turns a chapter or a question into a taught lesson — not a wall of text.

1. **Understands the source.** Parses PDF, DOCX, PPTX and text across English, Hindi and
   Bengali, then indexes it with BGE-M3 hybrid retrieval and cross-encoder reranking.
2. **Plans a curriculum.** Breaks the material into concepts, sequences them intro → core →
   advanced, and fits them to the learner's time budget.
3. **Teaches on video.** Each concept becomes a narrated segment: neural TTS, 24 FPS
   lip-synced visemes, and a rendered visual board (LaTeX, graphs, diagrams, code),
   composited to 1080p with FFmpeg.
4. **Checks and adapts.** Checkpoint answers are graded live against a rubric. A miss
   re-teaches the concept with a different analogy; repeated misses re-plan the lesson;
   persistent ones escalate to a human.
5. **Remembers everything.** Every concept, attempt, answer and misconception is stored
   against the learner's account and rolled up into their mastery profile.

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │   Browser (vanilla JS, no build)    │
                        │  landing · auth · dashboard ·       │
                        │  builder · classroom · report ·     │
                        │  history · analytics · settings     │
                        └──────────────┬──────────────────────┘
                     REST (JWT)        │        WebSocket (ticket)
                        ┌──────────────▼──────────────────────┐
                        │        FastAPI application          │
                        │  auth · account · lessons ·         │
                        │  dashboard · live classroom         │
                        └──────┬───────────────────┬──────────┘
                               │                   │
                    ┌──────────▼────────┐  ┌───────▼─────────────────┐
                    │  SQLite (WAL)     │  │  Service container      │
                    │  users, lessons,  │  │                         │
                    │  nodes, answers,  │  └───────┬─────────────────┘
                    │  reports, tokens  │          │
                    └───────────────────┘          │
        ┌───────────────────┬────────────────────┬─┴──────────────────┐
        ▼                   ▼                    ▼                    ▼
┌───────────────┐  ┌─────────────────┐  ┌────────────────┐  ┌─────────────────┐
│ RAG engine    │  │ Orchestrator    │  │ ML core        │  │ Avatar & voice  │
│ parse · chunk │  │ 7-state FSM,    │  │ rubric grading │  │ Edge-TTS ·      │
│ BGE-M3 · RRF  │→ │ 5 agents,       │→ │ misconception  │  │ visemes ·       │
│ rerank        │  │ Gemini          │  │ taxonomy       │  │ FFmpeg 1080p    │
└───────────────┘  └─────────────────┘  └────────────────┘  └─────────────────┘
```

**Teaching FSM:** `UNDERSTAND → PLAN → EXPLAIN → DEMONSTRATE → QUESTION → EVALUATE →
ADAPT → CONTINUE → DONE`, with `ADAPT` branching to `ALLOW`, `MODIFY`, `REGENERATE`
or `HUMAN`.

---

## Quick start

### 1. Prerequisites

- Python 3.10+ (macOS, Linux, or WSL)
- `ffmpeg` on `PATH` — or nothing at all, since `imageio-ffmpeg` bundles a binary
- Optional: `tesseract` for OCR on scanned PDFs

### 2. Install

```bash
git clone https://github.com/Sagnik120/Shikshak_AI.git
cd Shikshak_AI

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Then edit `.env`:

| Variable | Needed for | Notes |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Live lesson planning and grading | From [Google AI Studio](https://aistudio.google.com/). Without it the system falls back to a deterministic offline adapter. |
| `SECRET_KEY` | Signing tokens | **Required in production.** `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `SMTP_USER` / `SMTP_PASSWORD` | Sending OTP emails | Gmail App Password ([create one](https://myaccount.google.com/apppasswords)). Leave blank locally — see below. |

> **Email in local development.** With SMTP unconfigured, verification and reset codes
> are written to `data/outbox/` and returned in the API response as `dev_otp`, which the
> UI displays. That keeps the whole signup flow demoable offline. Set
> `EMAIL_DEV_FALLBACK=false` in production so codes are never returned to the caller.

### 4. Run

```bash
python -m uvicorn modules.backend.src.main:app --host 0.0.0.0 --port 8000
```

The database is created on first start. Open **http://localhost:8000** and sign up.

API docs are at **http://localhost:8000/api/docs**.

---

## What's in the database

SQLite in WAL mode, so the classroom can write progress while the dashboard reads.

| Table | Holds |
| :--- | :--- |
| `users` | Account, bcrypt password hash, learning preferences, lockout state, token version |
| `otp_codes` | Hashed, expiring, single-use codes for verification and reset |
| `refresh_tokens` | Rotating sessions, stored as keyed digests, with device and IP |
| `documents` | Uploaded material, per-user, with detected chapters and key terms |
| `lessons` | One teaching session: plan, FSM checkpoint, status, watch time |
| `lesson_nodes` | Per-concept mastery, attempts, re-teaches, script, video path |
| `interactions` | Every question asked, answer given, grade, misconception, adaptation |
| `reports` | Final score, strong and weak areas, narrative feedback |
| `lesson_events` | Append-only timeline of everything that happened |
| `learner_profiles` | Rolling cross-lesson mastery, streaks, misconception counts |

---

## Security

| Concern | How it's handled |
| :--- | :--- |
| Passwords | bcrypt (cost 12) over a SHA-256 pre-hash, so passwords past 72 bytes aren't silently truncated |
| Sessions | Short-lived JWT access tokens + rotating refresh tokens; replaying a used refresh token revokes every session for that user |
| Password changes | Bump a `token_version` carried in the JWT, invalidating outstanding access tokens immediately |
| OTP | Hashed at rest, single-use, expiring, attempt-capped, with a resend cooldown |
| Brute force | Per-IP sliding-window limits on login, signup, OTP send and verify; account lockout after repeated failures. Client IP comes from the socket unless `TRUST_PROXY_HEADERS` is on, so `X-Forwarded-For` cannot be forged to evade limits |
| Account enumeration | `forgot-password` and `login` return identical responses for known and unknown emails |
| Media | Served only to the owning account, by lesson and node id, with a containment check against the media root — never by a caller-supplied path |
| Uploads | Extension allowlist, size cap, stored under a per-user directory |
| Transport | CORS restricted to configured origins; `nosniff`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy` on every response |
| Live classroom | The WebSocket takes a short-lived, single-purpose ticket, so access tokens never appear in a URL |

---

## Repository layout

```
Shikshak_AI/
├── modules/
│   ├── backend/src/
│   │   ├── main.py             # App, routers, static frontend, startup
│   │   ├── config.py           # Settings from environment
│   │   ├── security.py         # Hashing, JWT, OTP, token digests
│   │   ├── deps.py             # Current-user resolution, rate limiting
│   │   ├── db/                 # Engine, session factory, ORM models
│   │   ├── api/                # auth · account · lessons · dashboard · ws
│   │   ├── services/           # email · lessons & progress · FSM sessions
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── integrations/       # Service container wiring the AI modules
│   ├── frontend/src/           # Static site: HTML, css/, js/, js/pages/
│   ├── rag/                    # Parsing, chunking, indexing, retrieval
│   ├── ai_agent_orchestration/ # 5 agents + the teaching FSM
│   ├── ml_core/                # Grading, misconception diagnosis, adaptation
│   ├── avatar_voice/           # TTS, visemes, visual renderers, compositor
│   ├── mlops/                  # Telemetry and metrics
│   └── testing/                # Cross-module harnesses
├── docs/                       # Specs and operational guides
├── tests/                      # Root-level unit, integration, eval, smoke
└── scripts/                    # Preflight checks and diagnostics
```

---

## Deploying

### Docker (recommended)

```bash
cp .env.example .env          # fill in SECRET_KEY, GEMINI_API_KEY, SMTP_*
docker compose up --build
```

Named volumes keep the database, uploads and rendered video across restarts.

### Directly

```bash
python scripts/run_server.py
```

It reads `HOST`/`PORT` from `.env`, prints a preflight summary (database, email,
LLM, secret key) and warns about anything unsafe for production.

### Before going live

1. Set `SECRET_KEY` explicitly — otherwise it is generated into `data/.secret_key`,
   and losing that file signs every user out.
2. Set `ENVIRONMENT=production` and `EMAIL_DEV_FALLBACK=false`, so verification
   codes are never returned in an API response.
3. Configure `SMTP_USER` / `SMTP_PASSWORD` so OTP emails actually send.
4. Set `CORS_ORIGINS` and `PUBLIC_BASE_URL` to your real domain.
5. Terminate TLS at a reverse proxy, then set `TRUST_PROXY_HEADERS=true` so the
   rate limiter reads the real client address from `X-Forwarded-For`. Leave it
   `false` when the app is exposed directly — otherwise a client can forge that
   header per request and bypass every rate limit.

> **Scaling note.** The teaching FSM holds per-lesson state in process memory, so
> run a single worker per instance and put session affinity in front of multiple
> instances. Lesson progress itself is in SQLite, so a learner can always resume;
> the in-memory state is only a cache that `SessionManager` rebuilds on demand.

---

## Testing

```bash
# Backend: auth, accounts, lessons, isolation, security primitives
pytest modules/backend/tests -v

# Everything
pytest modules/ tests/ -q
```

Backend tests run against a throwaway SQLite database created per test, so they never
touch your real data.

---

## Documentation

- [Inter-module contract](instructions/Contract.md) — canonical schemas
- [Documentation hub](docs/README.md)
- [Technical audit](docs/system/technical_audit.md)
- [Issues and postmortems](docs/system/issues_faced.md)
