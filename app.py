#!/usr/bin/env python3
"""Entrypoint for Hugging Face Spaces (Gradio SDK).

Runs the Shikshak AI FastAPI platform via uvicorn.run string import to ensure
clean process management and persistent event loop handling.
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Ensure required persistent runtime directories exist
for folder in ["data/storage", "data/media", "data/outbox", "chroma_db"]:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", 7860)))
    time.sleep(1)
    print(f"\n========================================================")
    print(f"  Shikshak AI — Starting production server on 0.0.0.0:{port}")
    print(f"========================================================\n")
    uvicorn.run(
        "modules.backend.src.main:app",
        host="0.0.0.0",
        port=port,
        timeout_keep_alive=75,
    )
