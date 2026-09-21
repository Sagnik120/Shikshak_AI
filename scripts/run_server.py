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


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    # Cloud environments (Render, Railway, Heroku, Fly, Cloud Run) provide $PORT or $RENDER.
    # Never enable reloader in cloud deployments: file writes to SQLite/data trigger
    # WatchFiles restart loops, which shut down the worker and cause port scan timeouts.
    is_cloud = bool(
        os.getenv("RENDER")
        or os.getenv("PORT")
        or os.getenv("DYNO")
        or os.getenv("FLY_APP_NAME")
        or os.getenv("K_SERVICE")
        or os.getenv("ENVIRONMENT", "").strip().lower() == "production"
    )
    reload_enabled = (settings.environment == "development") and not is_cloud

    print(f"\nShikshak AI — starting on http://{host}:{port}\n")
    preflight()
    print()

    kwargs = {
        "host": host,
        "port": port,
        "reload": reload_enabled,
        "timeout_keep_alive": 75,
    }
    if reload_enabled:
        kwargs["reload_dirs"] = [str(ROOT / "modules"), str(ROOT / "scripts")]
        kwargs["reload_excludes"] = ["data/*", "chroma_db/*", "*.db*", "*.wal", "*.shm", "storage/*"]

    uvicorn.run("modules.backend.src.main:app", **kwargs)


if __name__ == "__main__":
    main()
