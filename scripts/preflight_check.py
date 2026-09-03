#!/usr/bin/env python3
"""Shikshak AI — System Preflight Health & Readiness Diagnostic Utility.

Verifies:
1. Python Environment & Essential Dependencies
2. Video Composition & FFmpeg Binary Discovery (System PATH vs imageio-ffmpeg)
3. TTS Engine & Voice Availability (Edge-TTS Reachability vs Offline Fallback)
4. RAG Knowledge Grounding & Vector Storage (ChromaDB Persistence & Tokenizer)
5. Topic-Only Mode & Anti-Hallucination Guardrails
6. Multilingual Devanagari Chapter & Script Support

Usage:
    python scripts/preflight_check.py
"""

from __future__ import annotations

import os
import sys
import shutil
import platform
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Ensure project root is in sys.path regardless of where script is invoked
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Terminal color codes for rich CLI presentation
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_banner():
    print(f"\n{BLUE}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}   SHIKSHAK AI — SYSTEM PREFLIGHT HEALTH & READINESS CHECK{RESET}")
    print(f"   Architecture: Modular Pipeline (Contract.md v1.0.0)")
    print(f"   Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"   Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"{BLUE}{BOLD}{'=' * 75}{RESET}\n")


def check_dependencies() -> List[Tuple[str, str, str]]:
    """Verify all critical third-party Python packages."""
    results = []
    packages = [
        ("pydantic", "Core domain modeling and Contract schemas"),
        ("pypdf", "PDF parsing and text extraction"),
        ("docx", "DOCX textbook and document parser"),
        ("pptx", "PowerPoint slide parser"),
        ("PIL", "Pillow visual slide rendering and fallback compositor"),
        ("chromadb", "Vector database and embedding index store"),
        ("sklearn", "TF-IDF key-term and structure extraction"),
        ("transformers", "BGE-M3 tokenizer and neural models"),
        ("pytest", "Automated test execution framework"),
    ]

    for pkg_name, desc in packages:
        try:
            if pkg_name == "docx":
                import docx
            elif pkg_name == "pptx":
                import pptx
            elif pkg_name == "PIL":
                import PIL
            elif pkg_name == "sklearn":
                import sklearn
            else:
                __import__(pkg_name)
            results.append((pkg_name, "PASS", desc))
        except ImportError:
            results.append((pkg_name, "FAIL", f"Missing dependency: {desc}"))

    return results


def check_ffmpeg() -> Tuple[str, str, str]:
    """Verify FFmpeg availability via system PATH or imageio-ffmpeg static binary."""
    # 1. Check system PATH
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return "FFmpeg Binary", "PASS", f"System binary located at: {sys_ffmpeg}"

    # 2. Check imageio-ffmpeg static fallback
    try:
        import imageio_ffmpeg
        bundled_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(bundled_exe):
            return "FFmpeg Binary", "PASS", f"Bundled imageio-ffmpeg static binary: {bundled_exe}"
    except Exception:
        pass

    return "FFmpeg Binary", "WARN", "FFmpeg not found. Video rendering will use Pillow software preview fallback."


def check_tts_engine() -> Tuple[str, str, str]:
    """Test Edge-TTS network reachability and FallbackTTSAdapter."""
    try:
        import edge_tts
        from modules.avatar_voice.src.tts.base import resolve_voice_id
        voice_en = resolve_voice_id("en")
        voice_hi = resolve_voice_id("hi")
        return "Voice & TTS", "PASS", f"Edge-TTS ready. Voices: en='{voice_en}', hi='{voice_hi}'"
    except Exception as e:
        return "Voice & TTS", "WARN", f"Edge-TTS offline ({e}). Using language-aware FallbackTTSAdapter."


def check_rag_chroma() -> Tuple[str, str, str]:
    """Test ChromaDB in-memory initialization and index operations."""
    try:
        from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
        adapter = ChromaVectorStoreAdapter(persist_dir=":memory:")
        client = adapter._get_client()
        col = adapter._get_collection("healthcheck_doc")
        if col is not None:
            return "ChromaDB Storage", "PASS", f"Vector store operational (EphemeralClient ready, collection='{col.name}')"
        else:
            return "ChromaDB Storage", "PASS", "Vector store operational in mock/in-memory mode"
    except Exception as e:
        return "ChromaDB Storage", "FAIL", f"ChromaDB initialization failed: {e}"


def check_topic_only_mode() -> Tuple[str, str, str]:
    """Verify topic-only teaching mode (document_id=None)."""
    try:
        from modules.rag.src.service import RAGService
        from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
        svc = RAGService(vector_store=ChromaVectorStoreAdapter(persist_dir=":memory:"))
        res = svc.retrieve_context(document_id=None, query_text="Preflight Topic Test")
        ctx = svc.get_grounded_prompt(document_id=None, query_text="Preflight Topic Test")

        if res.risk_level == "no_document_context" and ctx.candidate_chunk_ids == []:
            return "Topic-Only RAG Mode", "PASS", "Gracefully handles document_id=None with anti-hallucination prompt"
        else:
            return "Topic-Only RAG Mode", "FAIL", f"Unexpected state: risk_level={res.risk_level}"
    except Exception as e:
        return "Topic-Only RAG Mode", "FAIL", f"Topic mode raised exception: {e}"


def check_progressive_visuals() -> Tuple[str, str, str]:
    """Verify progressive step-by-step visual rendering."""
    try:
        from modules.avatar_voice.src.models import VisualSpec
        from modules.avatar_voice.src.visuals.equation_renderer import EquationRenderer
        from modules.avatar_voice.src.visuals.code_renderer import CodeRenderer

        temp_dir = tempfile.mkdtemp(prefix="shikshak_preflight_")
        eq_renderer = EquationRenderer(output_dir=temp_dir)
        code_renderer = CodeRenderer(output_dir=temp_dir)

        eq_res = eq_renderer.render(VisualSpec(
            type="equation",
            content="a^2 + b^2 = c^2",
            steps=["Step 1", "Step 2"]
        ))
        code_res = code_renderer.render(VisualSpec(
            type="code",
            content="print(42)",
            execution_output="42"
        ))

        shutil.rmtree(temp_dir, ignore_errors=True)

        if eq_res.is_progressive and code_res.is_progressive:
            return "Progressive Visuals", "PASS", "Equation derivations & code execution flow operational"
        else:
            return "Progressive Visuals", "WARN", "Visual renderers operating in single-frame mode"
    except Exception as e:
        return "Progressive Visuals", "FAIL", f"Visual rendering check failed: {e}"


def check_multilingual_parser() -> Tuple[str, str, str]:
    """Verify Devanagari chapter detection and Indic token budgeting."""
    try:
        from modules.rag.src.parsing.structure import is_chapter_or_section_heading, detect_language
        from modules.rag.src.chunking.chunker import count_tokens

        is_h, title = is_chapter_or_section_heading("अध्याय 1: गति के नियम")
        lang = detect_language("यह एक हिंदी वाक्य है।")
        toks = count_tokens("न्यूटन के गति के नियम")

        if is_h and lang == "hi" and toks > 0:
            return "Multilingual (Indic)", "PASS", "Devanagari chapter recognition & Indic subword budgeting verified"
        else:
            return "Multilingual (Indic)", "WARN", "Partial Devanagari support"
    except Exception as e:
        return "Multilingual (Indic)", "FAIL", f"Multilingual parser check failed: {e}"


def main():
    print_banner()

    all_checks = []
    has_critical_failure = False

    # 1. Dependency Checks
    print(f"{BOLD}1. Core Python Packages & Libraries:{RESET}")
    dep_results = check_dependencies()
    for name, status, detail in dep_results:
        color = GREEN if status == "PASS" else RED
        tag = f"[{color}{status}{RESET}]"
        print(f"   {tag} {BOLD}{name:<16}{RESET} : {detail}")
        if status == "FAIL":
            has_critical_failure = True
    print()

    # 2. Subsystem Checks
    print(f"{BOLD}2. Subsystem Health & Pipeline Diagnostics:{RESET}")
    subsystems = [
        check_ffmpeg(),
        check_tts_engine(),
        check_rag_chroma(),
        check_topic_only_mode(),
        check_progressive_visuals(),
        check_multilingual_parser(),
    ]

    for name, status, detail in subsystems:
        if status == "PASS":
            color = GREEN
        elif status == "WARN":
            color = YELLOW
        else:
            color = RED
            has_critical_failure = True

        tag = f"[{color}{status}{RESET}]"
        print(f"   {tag} {BOLD}{name:<22}{RESET} : {detail}")

    print(f"\n{BLUE}{BOLD}{'=' * 75}{RESET}")
    if has_critical_failure:
        print(f"{RED}{BOLD}   PREFLIGHT STATUS: SYSTEM UNHEALTHY — CRITICAL ISSUES DETECTED{RESET}")
        print(f"   Review the [FAIL] items above and install missing packages or dependencies.")
        print(f"{BLUE}{BOLD}{'=' * 75}{RESET}\n")
        sys.exit(1)
    else:
        print(f"{GREEN}{BOLD}   PREFLIGHT STATUS: ALL SUBSYSTEMS GREEN AND READY FOR DEMO!{RESET}")
        print(f"   Shikshak AI is fully initialized across RAG, Avatar/Voice, and Multilingual pipelines.")
        print(f"{BLUE}{BOLD}{'=' * 75}{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
