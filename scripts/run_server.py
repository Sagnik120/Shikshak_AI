#!/usr/bin/env python3
"""Start the Shikshak AI server with the configured host and port.

Equivalent to invoking uvicorn directly, but reads HOST/PORT from .env and
prints the checks worth seeing before a demo.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from modules.backend.src.config import settings  # noqa: E402


def preflight() -> None:
    print(f"  Database        {settings.database_url}")
    print(f"  Environment     {settings.environment}")

    if settings.smtp_configured:
        print(f"  Email           SMTP via {settings.smtp_host} as {settings.smtp_user}")
    else:
        print("  Email           NOT CONFIGURED — codes go to data/outbox/ and the API response")
        if settings.environment == "production":
            print("                  ^ set SMTP_USER and SMTP_PASSWORD before going live")

    if os.getenv("GEMINI_API_KEY", "").strip():
        print("  LLM             Gemini (live)")
    else:
        print("  LLM             offline fallback adapter — set GEMINI_API_KEY for real lessons")

    if not os.getenv("SECRET_KEY", "").strip():
        print("  Secret key      generated and stored in data/.secret_key")
        if settings.environment == "production":
            print("                  ^ set SECRET_KEY explicitly in production")

    if settings.environment == "production" and settings.email_dev_fallback:
        print("\n  WARNING: EMAIL_DEV_FALLBACK is on in production, which returns OTP")
        print("           codes to the caller. Set EMAIL_DEV_FALLBACK=false.\n")

    if settings.environment == "production":
        _production_warnings()


def _production_warnings() -> None:
    """Flag the deploy-time footguns that are invisible until they bite."""
    db_path = str(settings.database_url).replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = str(settings.project_root / db_path)

    # Hosts like Render give a container an ephemeral filesystem: everything
    # written is discarded on every deploy and restart. Only SQLite is
    # supported, so without a mounted disk the database, uploads, rendered
    # videos and the Chroma index all reset — accounts included.
    print("\n  WARNING: all state is on the local filesystem:")
    print(f"             database  {db_path}")
    print(f"             uploads   {settings.upload_root}")
    print(f"             media     {settings.media_root}")
    print(f"             index     {os.getenv('CHROMA_PERSIST_DIR', './chroma_db')}")
    print("           If this host has an ephemeral filesystem (Render free tier,")
    print("           Heroku, most container PaaS), every deploy or restart wipes")
    print("           accounts, lessons and uploads. Mount a persistent disk at")
    print("           the data directory before taking real users.")

    print("\n  WARNING: retrieval models are loaded lazily on the FIRST document")
    print("           upload, not at startup. Defaults need roughly:")
    print("             BAAI/bge-m3              ~2.4 GB resident")
    print("             BAAI/bge-reranker-v2-m3  ~1.3 GB on top of that")
    print("           An instance smaller than ~4 GB will be OOM-killed the first")
    print("           time a learner uploads a file. For a small instance set")
    print("           EMBEDDING_BACKEND/EMBEDDING_MODEL to a MiniLM-sized model")
    print("           and RERANKER_ENABLED=false.\n")


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = settings.environment == "development"

    print(f"\nShikshak AI — starting on http://{host}:{port}\n")
    preflight()
    print()

    uvicorn.run(
        "modules.backend.src.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        # Renders block a worker for ~30s, so keep the default loop responsive.
        timeout_keep_alive=75,
    )


if __name__ == "__main__":
    main()
