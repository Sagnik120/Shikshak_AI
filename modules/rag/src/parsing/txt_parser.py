"""Markdown and plain text parser splitting by Markdown headings or paragraphs."""

from __future__ import annotations

import re
import logging
from typing import List, Tuple

from modules.rag.src.models import RawSection
from modules.rag.src.parsing.structure import is_chapter_or_section_heading

logger = logging.getLogger(__name__)


def parse_text_or_markdown(text: str) -> Tuple[List[RawSection], List[str]]:
    """Parse Markdown or plain text into sections based on Markdown headers or double-newlines.

    Args:
        text: String content of the document.

    Returns:
        Tuple of (raw_sections, detected_chapters)
    """
    sections: List[RawSection] = []
    chapters: List[str] = []

    lines = text.splitlines()
    current_heading: str | None = None
    current_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        is_heading = False
        heading_text = None
        level = 1

        # 1. Detect Markdown headings e.g. "# Title", "## Chapter 1", "### Section"
        heading_match = re.match(r'^(#{1,3})\s+(.*)$', stripped)
        if heading_match:
            is_heading = True
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
        else:
            # 2. Detect Devanagari / Latin chapter markers (e.g. "अध्याय 1: गति", "Chapter 2: Motion")
            is_explicit_heading, explicit_title = is_chapter_or_section_heading(stripped)
            if is_explicit_heading and explicit_title:
                is_heading = True
                level = 1
                heading_text = explicit_title

        if is_heading and heading_text:
            if current_lines:
                raw_block = "\n".join(current_lines).strip()
                if raw_block:
                    sections.append(
                        RawSection(
                            section_title=current_heading,
                            page_or_slide=None,
                            raw_text=raw_block,
                            metadata={"level": level}
                        )
                    )
                current_lines = []

            current_heading = heading_text
            if level <= 2 and heading_text not in chapters:
                chapters.append(heading_text)
        else:
            current_lines.append(line)

    # Flush final accumulated block
    if current_lines:
        raw_block = "\n".join(current_lines).strip()
        if raw_block:
            sections.append(
                RawSection(
                    section_title=current_heading,
                    page_or_slide=None,
                    raw_text=raw_block,
                    metadata={}
                )
            )

    # Edge Case: If no headings were detected (plain text), split on double newlines
    if not sections and text.strip():
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for idx, p in enumerate(paragraphs):
            sections.append(
                RawSection(
                    section_title=None,
                    page_or_slide=None,
                    raw_text=p,
                    metadata={"paragraph_index": idx}
                )
            )

    return sections, chapters
