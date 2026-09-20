#!/usr/bin/env python3
"""Entrypoint for Hugging Face Spaces (Gradio SDK).

Mounts the full Shikshak AI FastAPI platform and serves it on port 7860.
The complete SPA (Landing, Auth, Dashboard, Classroom, etc.) runs on the root '/'.
A companion Gradio interface is mounted on '/gradio'.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Ensure required persistent runtime directories exist
for folder in ["data/storage", "data/media", "data/outbox", "chroma_db"]:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

import uvicorn
from modules.backend.src.main import app

try:
    import gradio as gr

    with gr.Blocks(title="Shikshak AI (शिक्षक AI)") as demo:
        gr.Markdown(
            """
            # 🎓 Shikshak AI (शिक्षक AI)
            **Autonomous, Multimodal AI Educator with Real-Time Pedagogical Adaptation & Viseme Lip-Synced Video Instruction**

            The full interactive platform is running on the main interface:
            👉 [**Open Shikshak AI Full Application**](/)
            """
        )

    # Mount Gradio at /gradio so root '/' remains our custom Vanilla JS SPA
    app = gr.mount_gradio_app(app, demo, path="/gradio")
except Exception as err:
    print(f"Notice: Gradio wrapper skipped ({err}). Serving raw FastAPI application.")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    print(f"\n========================================================")
    print(f"  Shikshak AI — Launching on Hugging Face Spaces (Port {port})")
    print(f"========================================================\n")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        timeout_keep_alive=75,
    )
