# Shikshak AI — backend image (Hugging Face Spaces / Render / any Docker host)
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

# Hugging Face Spaces runs the container as uid 1000, so everything the app
# writes (SQLite, uploads, rendered video, model cache) must be owned by it.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /app

COPY requirements.txt .
# CPU-only torch first: the default Linux wheel bundles CUDA (~2.5 GB) that a
# CPU host never uses. requirements.txt then sees torch as already satisfied.
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

# Small-host retrieval profile (~0.6 GB resident instead of ~3.8 GB for
# BGE-M3 + cross-encoder). Override with env vars on a bigger machine.
ENV EMBEDDING_BACKEND=e5 \
    EMBEDDING_MODEL=intfloat/multilingual-e5-small \
    RERANKER_ENABLED=false \
    RENDER_WORKERS=2 \
    ENVIRONMENT=production \
    PORT=7860

USER user
# Bake the models into the image so the first learner doesn't wait on a download.
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('intfloat/multilingual-e5-small'); S('all-MiniLM-L6-v2'); from transformers import AutoTokenizer as T; T.from_pretrained('BAAI/bge-m3')"
# Everything is cached now; skip the Hub's per-load update checks (~2 s of
# HTTP on every cold start). Unset this if you switch to an un-baked model.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY --chown=user . .
RUN mkdir -p data/storage data/media data/outbox chroma_db

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD curl -fsS http://localhost:${PORT:-7860}/health || exit 1

CMD ["python", "scripts/run_server.py"]
