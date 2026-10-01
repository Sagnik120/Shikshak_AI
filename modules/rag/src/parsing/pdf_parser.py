"""PDF parser extracting text, page structure, section headings, and OCR fallback."""

from __future__ import annotations

import io
import re
import logging
from typing import List, Tuple

from modules.rag.src.models import RawSection
from modules.rag.src.parsing.ocr import extract_text_from_pdf_page_ocr
from modules.rag.src.parsing.structure import is_chapter_or_section_heading

logger = logging.getLogger(__name__)


def _line_key(line: str) -> str:
    """A line with its digits masked, so "Page 2" and "Page 3" compare equal."""
    return re.sub(r"\d+", "#", line.strip().lower())


def _edge_lines(text: str) -> List[str]:
    """Where running headers and footers live: a page's first and last lines."""
    lines = [line for line in text.split("\n") if line.strip()]
    return lines[:2] + lines[-2:]


def _repeated_lines(page_texts: List[str]) -> set:
    """Short edge-of-page lines on most pages: running headers and footers.

    Only a page's first/last lines are considered, so a sentence that really
    does repeat in the body of several pages is never stripped.
    """
    if len(page_texts) < 3:
        return set()
    counts: dict[str, int] = {}
    for text in page_texts:
        for key in {_line_key(line) for line in _edge_lines(text) if 0 < len(line.strip()) <= 100}:
            counts[key] = counts.get(key, 0) + 1
    need = max(3, int(len(page_texts) * 0.6 + 0.999))
    return {key for key, n in counts.items() if n >= need}


def parse_pdf(file_bytes: bytes) -> Tuple[List[RawSection], List[str]]:
    """Parse a PDF document into raw sections per page/heading and extract chapter titles.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file.

    Returns:
        Tuple of (raw_sections, detected_chapters)
    """
    sections: List[RawSection] = []
    chapters: List[str] = []
    
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        num_pages = len(reader.pages)
        
        # Check outlines/bookmarks if available for high-fidelity chapter detection
        try:
            outlines = reader.outline
            if outlines:
                for item in outlines:
                    if hasattr(item, 'title') and isinstance(item.title, str) and item.title.strip():
                        chapters.append(item.title.strip())
                    elif isinstance(item, dict) and "/Title" in item:
                        chapters.append(str(item["/Title"]).strip())
        except Exception:
            pass

        current_heading: str | None = None
        page_texts = [page.extract_text() or "" for page in reader.pages]
        # Running headers/footers ("Chapter 9 — Class 9 Science", "Page 3")
        # repeat on most pages: they are noise in every chunk, and a running
        # header as each page's first line hid the real headings below it.
        repeated = _repeated_lines(page_texts)

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            page_text = page_texts[idx]
            if repeated:
                # Strip them only where they appear: at the page's edges.
                lines = page_text.split("\n")
                non_empty = [i for i, line in enumerate(lines) if line.strip()]
                edge_idx = set(non_empty[:2] + non_empty[-2:])
                page_text = "\n".join(
                    line for i, line in enumerate(lines)
                    if not (i in edge_idx and _line_key(line) in repeated)
                )

            # Edge Case §5.1: Scanned / Image-only PDF with near-zero extractable text
            page_warning = None
            if len(page_text.strip()) < 30:
                ocr_text, conf = extract_text_from_pdf_page_ocr(file_bytes, page_num)
                if len(ocr_text.strip()) > len(page_text.strip()):
                    page_text = ocr_text
                else:
                    page_warning = f"Page {page_num} appears to be a scanned image with minimal text; OCR unavailable or incomplete."

            if not page_text.strip():
                if page_warning:
                    sections.append(
                        RawSection(
                            section_title=None,
                            page_or_slide=page_num,
                            raw_text="",
                            metadata={"page": page_num, "warning": page_warning}
                        )
                    )
                continue

            sec_meta = {"page": page_num}
            if page_warning:
                sec_meta["warning"] = page_warning

            # Split the page at every heading line (not only its first line),
            # so each section is chunked and cited under its own title.
            page_lines = [line.strip() for line in page_text.split("\n") if line.strip()]
            blocks: List[Tuple[str | None, List[str]]] = [(current_heading, [])]
            for line in page_lines:
                is_heading, heading_title = is_chapter_or_section_heading(line)
                if is_heading and heading_title:
                    current_heading = heading_title
                    if current_heading not in chapters:
                        chapters.append(current_heading)
                    blocks.append((current_heading, [line]))
                else:
                    blocks[-1][1].append(line)

            # No recognised heading on the page: keep the old loose first-line
            # heuristic for documents without numbered headings.
            if len(blocks) == 1 and page_lines:
                first_line = page_lines[0]
                if (
                    re.match(r'^(Chapter|Section|\d+(\.\d+)*)\s+', first_line, re.IGNORECASE)
                    or (first_line.isupper() and len(first_line) < 60)
                    or (len(first_line.split()) <= 6 and len(first_line) < 50 and not first_line.endswith('.'))
                ):
                    current_heading = first_line
                    if current_heading not in chapters:
                        chapters.append(current_heading)
                    blocks = [(current_heading, page_lines)]

            for title, lines in blocks:
                text = "\n".join(lines).strip()
                if not text:
                    continue
                sections.append(
                    RawSection(
                        section_title=title,
                        page_or_slide=page_num,
                        raw_text=text,
                        metadata=dict(sec_meta),
                    )
                )

    except Exception as e:
        logger.error(f"pypdf failed to parse PDF: {e}")
        # Fallback to pdfplumber if installed
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_num = idx + 1
                    text = page.extract_text() or ""
                    if text.strip():
                        sections.append(
                            RawSection(
                                section_title=None,
                                page_or_slide=page_num,
                                raw_text=text.strip(),
                                metadata={"page": page_num}
                            )
                        )
        except Exception as e2:
            logger.error(f"pdfplumber fallback also failed: {e2}")

    return sections, chapters
