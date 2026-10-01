# Shikshak — web (Next.js)

The learner, mentor and admin web app for Shikshak AI. It talks to the FastAPI
backend in `modules/backend` over REST and the classroom WebSocket. The older
static frontend in `modules/frontend` is untouched and still works.

## Run it locally

```bash
# 1. backend (from the repo root)
uvicorn modules.backend.src.main:app --port 8000

# 2. web
cd FRONTEND
pnpm install
pnpm dev            # http://localhost:3000
```

The backend's default CORS list already allows `localhost:3000` and `127.0.0.1:3000`.

| Variable | Default | What it does |
|---|---|---|
| `ADMIN_SIGNUP_CODE` (backend) | `SHIKSHAK-ADMIN` outside production; unset = staff sign-up closed in production | Access code required by the staff sign-up form `/staff/signup`. |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` | Backend origin for REST, media and the WebSocket (`wss://` is used automatically for `https://`). Baked in at build time. |

Demo accounts (seeded by the backend; password = `DEFAULT_DEMO_PASSWORD`, default `DemoStudent@123`):
`demo@shikshak.ai` (learner), `teacher@shikshak.ai` and `admin@shikshak.ai` (open **Admin**).

## Deploy (Vercel)

1. New project → root directory `FRONTEND`, framework Next.js.
2. Set `NEXT_PUBLIC_BACKEND_URL` to the deployed backend's origin.
3. On the backend, add the Vercel domain to `CORS_ORIGINS` (comma-separated).

## Map

| Route | What |
|---|---|
| `/` | Landing page: live mini-lesson that pauses and asks, 3D paper plane, scroll story |
| `/staff/login` `/staff/signup` | Staff (admin/teacher) sign-in → straight to `/admin`; sign-up needs the staff access code. Student accounts are refused here |
| `/login` `/signup` `/verify` `/forgot` `/reset` | Auth. The OTP is shown on screen (no email is sent), with "Fill it in for me" |
| `/dashboard` | Needs-attention, resume card, stats, activity, score trend |
| `/new` | Topic or uploaded notes → level, language, time → plan preview |
| `/learn/[id]` | The live classroom (see below) |
| `/review/[id]` | Rewatch saved videos; practice questions with instant feedback |
| `/report/[id]` | Score, per-concept timeline with answers, notes download |
| `/lessons` `/progress` `/profile` | Library (glass search), analytics, profile (photo upload or avatar) |
| `/admin` | Mission control: overview, live classrooms, mentor inbox, insights, AI quality, system health, learners |

### The classroom

`src/features/classroom/controller.ts` is a framework-free port of the original
classroom protocol. React reads it through `useSyncExternalStore`. It keeps the
original classroom's guarantees:

- Each answer carries its `interaction_id`.
- The video can't play or seek past an unanswered checkpoint.
- A reconnect (with backoff) never restarts a loaded video or clears a typed answer.
- A paused lesson never auto-starts.
- Rewatching an earlier concept pauses the live lesson and resumes it exactly where it was.

Layout:
- The checkpoint question opens over the paused video.
- Notes, Transcript, Questions and Source sit in a tabbed panel beside the video.
- The concept rail runs underneath.

## Code layout

```
src/core        api client, types, i18n (en.ts defines keys; hi.ts must match — the build fails otherwise)
src/providers   auth, i18n, query client
src/components  brand (logo, loader, avatars), layout (shell, cursor, ⌘K palette), ui, motion, landing
src/features    classroom
src/app         routes: (auth) split-screen, (app) with sidebar, (focus) full-screen classroom
```

## Checks

```bash
pnpm exec tsc --noEmit && pnpm exec eslint src && pnpm build
python scripts/e2e_next_frontend.py          # real browser vs. real backend (offline LLM)
python scripts/e2e_next_frontend.py --live   # with Gemini
python scripts/e2e_next_frontend.py --shots=/tmp/shots   # also save screenshots of each step
```
