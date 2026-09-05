#!/usr/bin/env python3
"""Shikshak AI — Unified Environment Setup & Model Downloader.

Automates the complete environment preparation for anyone cloning the repository:
1. Verifies & initializes required local directories (models/, chroma_db/, data/storage/, etc.).
2. Creates `.env` from `.env.example` if not already present.
3. Pre-caches ML Core & RAG embedding models:
   - sentence-transformers/all-MiniLM-L6-v2 (used for semantic answer evaluation in MLCoreService)
   - BAAI/bge-m3 (dense + sparse multilingual embeddings for RAG)
4. Downloads Tier 2 Neural Lip-Sync Avatar weights:
   - TMElyralab/MuseTalk -> models/musetalk/
5. Validates FFmpeg and TTS system readiness.

Usage:
    # Recommended quick setup (ML embeddings + directories + environment check):
    python scripts/setup_and_download_models.py

    # Full setup including Tier 2 MuseTalk neural avatar weights (~4 GB):
    python scripts/setup_and_download_models.py --all

    # Download only Tier 2 avatar weights:
    python scripts/setup_and_download_models.py --avatar-only

    # Verify existing models and environment without downloading:
    python scripts/setup_and_download_models.py --verify
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, List

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ANSI Color formatting
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(title: str):
    print(f"\n{BLUE}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}   {title}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 75}{RESET}")


def ensure_directories():
    """Ensure all runtime directories exist with proper permissions."""
    dirs_to_create = [
        REPO_ROOT / "models",
        REPO_ROOT / "models" / "musetalk",
        REPO_ROOT / "chroma_db",
        REPO_ROOT / "data" / "storage",
        REPO_ROOT / "output",
        REPO_ROOT / "temp_audio",
        REPO_ROOT / "rendered_videos",
    ]
    print(f"\n{BOLD}[1/5] Checking Directory Structure...{RESET}")
    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)
        rel_path = d.relative_to(REPO_ROOT)
        print(f"  {GREEN}✓{RESET} {rel_path}/ ready")


def ensure_environment_config():
    """Check if .env exists; copy from .env.example if missing."""
    print(f"\n{BOLD}[2/5] Checking Environment Configuration (.env)...{RESET}")
    env_path = REPO_ROOT / ".env"
    env_example = REPO_ROOT / ".env.example"

    if env_path.exists():
        print(f"  {GREEN}✓{RESET} .env exists.")
    elif env_example.exists():
        shutil.copy(env_example, env_path)
        print(f"  {YELLOW}⚠{RESET} Created .env from .env.example template.")
        print(f"    {YELLOW}→ Please edit .env and set your GEMINI_API_KEY if testing live generation.{RESET}")
    else:
        print(f"  {RED}✗{RESET} Neither .env nor .env.example found.")


def download_ml_embeddings():
    """Pre-cache sentence transformers and embedding models."""
    print(f"\n{BOLD}[3/5] Pre-caching ML & RAG Embedding Models...{RESET}")

    # 1. all-MiniLM-L6-v2 (Used by MLCore for student answer evaluation & similarity)
    try:
        print(f"  Downloading/Verifying {CYAN}sentence-transformers/all-MiniLM-L6-v2{RESET} (~90 MB)...")
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        test_emb = model.encode("Shikshak AI semantic verification")
        print(f"  {GREEN}✓{RESET} all-MiniLM-L6-v2 cached & verified (vector dim: {len(test_emb)}).")
    except ImportError:
        print(f"  {RED}✗{RESET} sentence-transformers is not installed. Run: pip install -r requirements.txt")
    except Exception as e:
        print(f"  {YELLOW}⚠{RESET} Could not load all-MiniLM-L6-v2: {e}")

    # 2. BAAI/bge-m3 (Multilingual Dense + Sparse embeddings for RAG)
    try:
        print(f"  Checking {CYAN}BAAI/bge-m3{RESET} multilingual model...")
        # Note: BGE-M3 is ~2.2 GB. We check if flag_embedding or sentence_transformers can load it
        from sentence_transformers import SentenceTransformer
        print(f"  Pre-caching BAAI/bge-m3 (optional, fallback to MiniLM if offline)...")
        bge = SentenceTransformer("BAAI/bge-m3")
        print(f"  {GREEN}✓{RESET} BAAI/bge-m3 multilingual embeddings ready.")
    except Exception as e:
        print(f"  {YELLOW}ℹ{RESET} BAAI/bge-m3 not pre-cached ({e}). RAG adapter will auto-fallback gracefully.")


def download_musetalk_weights():
    """Download Tier 2 MuseTalk model weights into models/musetalk/."""
    print(f"\n{BOLD}[4/5] Downloading Tier 2 Avatar Weights (TMElyralab/MuseTalk)...{RESET}")
    musetalk_dir = REPO_ROOT / "models" / "musetalk"

    # Check if weights already present
    expected_files = ["musetalk.json", "pytorch_model.bin", "unet.bin", "model.safetensors"]
    existing = [f for f in expected_files if (musetalk_dir / f).exists()]

    if existing:
        print(f"  {GREEN}✓{RESET} MuseTalk weights already present in {musetalk_dir.relative_to(REPO_ROOT)} ({len(existing)} checkpoints found).")
        return

    try:
        from huggingface_hub import snapshot_download
        print(f"  Connecting to Hugging Face repository {CYAN}TMElyralab/MuseTalk{RESET}...")
        print(f"  Destination: {musetalk_dir.relative_to(REPO_ROOT)}")
        print(f"  {YELLOW}Note: This is ~4 GB of weights. Download speed depends on your internet connection.{RESET}")

        snapshot_download(
            repo_id="TMElyralab/MuseTalk",
            local_dir=str(musetalk_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        print(f"  {GREEN}✓{RESET} MuseTalk model weights successfully downloaded to {musetalk_dir.relative_to(REPO_ROOT)}.")
    except ImportError:
        print(f"  {RED}✗{RESET} huggingface_hub is not installed. Run: pip install huggingface_hub")
    except Exception as e:
        print(f"  {RED}✗{RESET} Failed to download MuseTalk weights: {e}")
        print(f"    {YELLOW}Reminder: Tier 1 2D Viseme synthesis runs without downloading Tier 2 weights!{RESET}")


def check_system_readiness():
    """Verify FFmpeg and speech synthesis toolchains."""
    print(f"\n{BOLD}[5/5] Checking Media & Toolchain Readiness...{RESET}")

    # Check FFmpeg
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"  {GREEN}✓{RESET} System FFmpeg found at: {ffmpeg_path}")
    else:
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"  {GREEN}✓{RESET} imageio-ffmpeg fallback binary found at: {exe}")
        except Exception:
            print(f"  {YELLOW}⚠{RESET} FFmpeg not found on PATH and imageio-ffmpeg missing. Video composition requires FFmpeg.")

    # Check Edge-TTS
    try:
        import edge_tts
        print(f"  {GREEN}✓{RESET} edge-tts package installed (multilingual neural voices).")
    except ImportError:
        print(f"  {YELLOW}⚠{RESET} edge-tts missing. Fallback acoustic synthesizer will be used.")


def verify_status():
    """Print complete environment and model audit."""
    print_header("SHIKSHAK AI — LOCAL ENVIRONMENT AUDIT")
    musetalk_dir = REPO_ROOT / "models" / "musetalk"
    chroma_dir = REPO_ROOT / "chroma_db"
    storage_dir = REPO_ROOT / "data" / "storage"

    print(f"{BOLD}Directories & Storage:{RESET}")
    print(f"  • Models Directory:    {musetalk_dir.parent} ({'Exists' if musetalk_dir.parent.exists() else 'Missing'})")
    print(f"  • Vector DB (Chroma):  {chroma_dir} ({'Exists' if chroma_dir.exists() else 'Missing'})")
    print(f"  • Document Storage:    {storage_dir} ({'Exists' if storage_dir.exists() else 'Missing'})")

    print(f"\n{BOLD}Avatar Tiers Available:{RESET}")
    print(f"  • {GREEN}Tier 1 (2D Visemes @ 24fps):{RESET} Active & Ready (Zero download needed, runs on any CPU)")
    
    expected_files = ["musetalk.json", "pytorch_model.bin", "unet.bin", "model.safetensors"]
    found_weights = [f for f in expected_files if (musetalk_dir / f).exists()]
    if found_weights:
        print(f"  • {GREEN}Tier 2 (MuseTalk Diffusion):{RESET} Weights installed ({len(found_weights)} checkpoints in models/musetalk/)")
    else:
        print(f"  • {YELLOW}Tier 2 (MuseTalk Diffusion):{RESET} Not installed (Run with --all to download, or use Tier 1 default)")

    print(f"\n{BOLD}Ready to Run:{RESET}")
    print(f"  1. Start Backend Server:  {CYAN}uvicorn modules.backend.src.main:app --reload --port 8000{RESET}")
    print(f"  2. Run Full Integration:  {CYAN}pytest modules/backend/tests/integration/test_full_chain_unmocked.py -v{RESET}")
    print(f"  3. Run All Test Suites:   {CYAN}pytest{RESET}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Shikshak AI Setup & Model Downloader")
    parser.add_argument("--all", action="store_true", help="Download all models (ML embeddings + Tier 2 MuseTalk weights)")
    parser.add_argument("--ml-only", action="store_true", help="Download only ML & RAG embedding models")
    parser.add_argument("--avatar-only", action="store_true", help="Download only Tier 2 MuseTalk avatar weights")
    parser.add_argument("--verify", action="store_true", help="Verify environment status without downloading")

    args = parser.parse_args()

    if args.verify:
        verify_status()
        return

    print_header("SHIKSHAK AI — ENVIRONMENT SETUP & MODEL DOWNLOADER")
    print(f"Target Project Root: {REPO_ROOT}")

    ensure_directories()
    ensure_environment_config()

    if args.avatar_only:
        download_musetalk_weights()
    elif args.ml_only:
        download_ml_embeddings()
    elif args.all:
        download_ml_embeddings()
        download_musetalk_weights()
    else:
        # Default: Fast developer setup (ML embeddings + checks, prompt for MuseTalk)
        download_ml_embeddings()
        print(f"\n{BOLD}[4/5] Tier 2 Neural Avatar (MuseTalk):{RESET}")
        print(f"  {YELLOW}ℹ Note:{RESET} Tier 1 2D Viseme synthesis runs out-of-the-box on your CPU.")
        print(f"  To download the ~4 GB Tier 2 MuseTalk checkpoint, run:")
        print(f"    {CYAN}python scripts/setup_and_download_models.py --avatar-only{RESET}")

    check_system_readiness()
    verify_status()


if __name__ == "__main__":
    main()
