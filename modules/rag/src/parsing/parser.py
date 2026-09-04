"""Unified document parsing engine mapping raw file bytes to ParsedDocument (Contract §4)."""

from __future__ import annotations

import os
import uuid
import logging
from typing import List, Tuple

from modules.rag.src.models import ParsedDocument, RawSection, DetectedStructure
from modules.rag.src.parsing.pdf_parser import parse_pdf
from modules.rag.src.parsing.docx_parser import parse_docx
from modules.rag.src.parsing.pptx_parser import parse_pptx
from modules.rag.src.parsing.txt_parser import parse_text_or_markdown
from modules.rag.src.parsing.structure import detect_language, extract_key_terms_tfidf
from modules.rag.src.chunking.chunker import chunk_sections

logger = logging.getLogger(__name__)


def extract_raw_sections(
    file_bytes: bytes,
    filename: str,
    mime_type: str = ""
) -> Tuple[List[RawSection], List[str]]:
    """Route file bytes to the appropriate parser based on extension and mime type.

    Returns:
        Tuple of (raw_sections, detected_chapters)
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf" or "pdf" in mime_type.lower():
        return parse_pdf(file_bytes)
    elif ext in (".docx", ".doc") or "word" in mime_type.lower() or "officedocument.wordprocessingml" in mime_type.lower():
        return parse_docx(file_bytes)
    elif ext in (".pptx", ".ppt") or "presentation" in mime_type.lower() or "powerpoint" in mime_type.lower():
        return parse_pptx(file_bytes)
    elif ext in (".txt", ".md", ".markdown", ".rst") or "text" in mime_type.lower():
        text = file_bytes.decode("utf-8", errors="replace")
        return parse_text_or_markdown(text)
    else:
        # Generic text fallback
        try:
            text = file_bytes.decode("utf-8", errors="replace")
            return parse_text_or_markdown(text)
        except Exception as e:
            logger.error(f"Unsupported file type '{ext}' and binary decode failed: {e}")
            return [], []


def parse_document(
    file_bytes: bytes,
    filename: str,
    mime_type: str = "",
    document_id: str | None = None
) -> ParsedDocument:
    """Parse raw uploaded file bytes into a contract-compliant ParsedDocument (Contract §4).

    Args:
        file_bytes: Raw bytes from the uploaded file (from UploadRequest).
        filename: Original file name including extension.
        mime_type: Optional MIME type string.
        document_id: Optional existing document ID; generates a UUID if not provided.

    Returns:
        ParsedDocument matching Contract §4 exactly.
    """
    doc_id = document_id or str(uuid.uuid4())
    raw_sections, chapters = extract_raw_sections(file_bytes, filename, mime_type)

    # Combine all raw text for language and TF-IDF key terms extraction
    full_text = "\n\n".join(sec.raw_text for sec in raw_sections if sec.raw_text.strip())
    
    source_lang = detect_language(full_text)
    key_terms = extract_key_terms_tfidf(full_text, top_n=15)

    # Chunk sections using structure-aware semantic chunker
    chunks = chunk_sections(raw_sections, document_id=doc_id)

    # Collect diagnostic warnings from raw sections and empty/scanned document checks
    warnings: List[str] = []
    for sec in raw_sections:
        warn = sec.metadata.get("warning")
        if warn and warn not in warnings:
            warnings.append(warn)

    if (not full_text.strip() or len(full_text.strip()) < 30) and len(file_bytes) > 200:
        empty_warn = "Document appears to contain scanned images or minimal extractable text; content may be incomplete."
        if empty_warn not in warnings:
            warnings.append(empty_warn)

    detected_structure = DetectedStructure(
        chapters=chapters,
        key_terms=key_terms
    )

    return ParsedDocument(
        document_id=doc_id,
        source_lang=source_lang,
        chunks=chunks,
        detected_structure=detected_structure,
        warnings=warnings
    )
