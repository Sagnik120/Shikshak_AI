# Shikshak AI — single-image deployment
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg for video compositing; the rest are build deps for the ML wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# SQLite, uploads and rendered media all live here — mount a volume to persist.
RUN mkdir -p data/storage data/media data/outbox chroma_db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# One worker: the teaching FSM keeps per-lesson state in process memory, and a
# second worker would not see it. Scale by running more instances behind a
# session-affine proxy rather than by adding workers here.
CMD ["uvicorn", "modules.backend.src.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--timeout-keep-alive", "75"]
