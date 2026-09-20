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

EXPOSE 8000 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

# Launch using the preflight server script which reads $PORT dynamically (HF Spaces uses 7860, Render uses $PORT)
CMD ["python", "scripts/run_server.py"]
