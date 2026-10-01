# Deploying Shikshak AI (free tier)

## Why two hosts

Vercel's free plan can't run the backend. Its Python functions are capped at a
250 MB bundle (this app's ML stack is ~1.7 GB), have no WebSocket server (the
classroom holds one open for the whole lesson), time out after 60 s (a video
render or first upload can take longer) and have a read-only disk (SQLite,
uploads and videos need to write).

So the app is split:

| Part | Host | Why |
|---|---|---|
| Frontend (`modules/frontend/src`, static HTML/JS) | **Vercel** | Global CDN, instant page loads |
| Backend (FastAPI + WebSocket + ffmpeg + models) | **Hugging Face Spaces** (Docker, free: 2 vCPU, 16 GB RAM) | Enough memory for the models, WebSockets work |

Measured with the image's settings: **~2.5 GB peak** for a full lesson
(models ~1.45 GB + video rendering), so 16 GB leaves room for several learners
at once. Renders are capped at 2 in parallel (`RENDER_WORKERS`).

---

## 1. Backend on Hugging Face Spaces

1. Create a Space at <https://huggingface.co/new-space>: SDK **Docker**, template **Blank**, hardware **CPU basic (free)**.
2. The Space's `README.md` must start with this header (add it at the top of the README you push):
   ```yaml
   ---
   title: Shikshak AI
   emoji: 🎓
   sdk: docker
   app_port: 7860
   ---
   ```
3. In the Space → **Settings → Variables and secrets**, add:

   | Name | Type | Value |
   |---|---|---|
   | `GEMINI_API_KEY` | Secret | your key |
   | `SECRET_KEY` | Secret | output of `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `CORS_ORIGINS` | Variable | `https://<your-project>.vercel.app` |
   | `CORS_ORIGIN_REGEX` | Variable (optional) | `^https://<your-project>(-[a-z0-9-]+)?\.vercel\.app$` (allows Vercel preview URLs) |
   | `PUBLIC_BASE_URL` | Variable | `https://<your-project>.vercel.app` |
   | `GEMINI_FALLBACK_MODEL` | Variable (optional) | a second model with its own quota, tried before the offline fallback |

   Do **not** set `ENABLE_SMTP_SEND`: OTP codes are shown on screen and never emailed.
4. Push this repository to the Space's git remote. The first build takes ~10 minutes (it bakes the models into the image, so the first learner doesn't wait on a download).
5. Check `https://<user>-<space>.hf.space/health` returns `{"status": "ok", ...}`.

## 2. Frontend on Vercel

1. <https://vercel.com/new> → import the repository.
2. **Root Directory:** `modules/frontend` (everything else is read from `modules/frontend/vercel.json`).
3. **Environment variable:** `SHIKSHAK_BACKEND_URL` = `https://<user>-<space>.hf.space`
   (the build fails with a clear message if it's missing or not https).
4. Deploy, then open the Vercel URL and sign up. The verification code appears on screen, with a "Fill it in for me" button.

## 3. Verify the deployment

From your machine, against the live backend:

```bash
curl -s https://<user>-<space>.hf.space/health
```

Locally, the full pipeline check (same code path as production) is:

```bash
python scripts/e2e_full_pipeline.py            # offline LLM, no quota used
python scripts/e2e_full_pipeline.py --live     # real Gemini
```

## Known free-tier limits

- **Data is not permanent.** A free Space's disk resets when it restarts or
  rebuilds, which wipes accounts, lessons and uploads. The demo accounts are
  re-created on every start. For real users, add HF persistent storage (paid)
  and point `DATABASE_URL`, `UPLOAD_ROOT`, `MEDIA_ROOT` and `CHROMA_PERSIST_DIR` at `/data`.
- **Sleep after inactivity.** A free Space sleeps after ~48 h without traffic;
  the next visit wakes it (about a minute).
- **Gemini free-tier rate limits.** Calls retry briefly on 429/5xx. If Gemini is
  still unavailable, that step is served by the offline teacher, which builds
  the lesson from the uploaded document and the topic instead of failing.

## Single-host alternative

The same `Dockerfile` also serves the frontend itself (same origin, no Vercel
needed). Deploy only step 1 and open the Space URL directly.
