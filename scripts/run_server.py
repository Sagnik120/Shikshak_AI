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
