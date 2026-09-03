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
        
        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            page_text = page.extract_text() or ""
            
            # Edge Case §5.1: Scanned / Image-only PDF with near-zero extractable text
            if len(page_text.strip()) < 30:
                ocr_text, conf = extract_text_from_pdf_page_ocr(file_bytes, page_num)
                if len(ocr_text.strip()) > len(page_text.strip()):
                    page_text = ocr_text

            if not page_text.strip():
                continue

            # Heuristic for chapter / heading detection on page text
            page_lines = [line.strip() for line in page_text.split("\n") if line.strip()]
            if page_lines:
                first_line = page_lines[0]
                is_heading, heading_title = is_chapter_or_section_heading(first_line)
                if not is_heading and (
                    re.match(r'^(Chapter|Section|\d+(\.\d+)*)\s+', first_line, re.IGNORECASE)
                    or (first_line.isupper() and len(first_line) < 60)
                    or (len(first_line.split()) <= 6 and len(first_line) < 50 and not first_line.endswith('.'))
                ):
                    is_heading = True
                    heading_title = first_line

                if is_heading and heading_title:
                    current_heading = heading_title
                    if current_heading not in chapters:
                        chapters.append(current_heading)

            sections.append(
                RawSection(
                    section_title=current_heading,
                    page_or_slide=page_num,
                    raw_text=page_text.strip(),
                    metadata={"page": page_num}
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
