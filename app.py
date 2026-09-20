#!/usr/bin/env python3
"""Entrypoint for Hugging Face Spaces (Gradio SDK).

Launches the Shikshak AI FastAPI platform on port 7860 with socket reuse
and graceful port retry to avoid [Errno 98] address collision during container starts.
"""
import os
import sys
import time
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Ensure required persistent runtime directories exist
for folder in ["data/storage", "data/media", "data/outbox", "chroma_db"]:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

import uvicorn
from modules.backend.src.main import app

def wait_for_port(port: int = 7860, max_retries: int = 6) -> int:
    """Wait for socket to be free from TIME_WAIT states before launching."""
    for i in range(max_retries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
            s.close()
            return port
        except OSError as e:
            s.close()
            print(f"Port {port} busy ({e}), waiting for socket release (attempt {i+1}/{max_retries})...")
            time.sleep(2)
    return port

if __name__ == "__main__":
    target_port = int(os.getenv("PORT", os.getenv("GRADIO_SERVER_PORT", 7860)))
    port = wait_for_port(target_port)

    print(f"\n========================================================")
    print(f"  Shikshak AI — Binding server to 0.0.0.0:{port}")
    print(f"========================================================\n")

    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        timeout_keep_alive=75,
        log_level="info",
    )
    server = uvicorn.Server(config)
    server.run()
