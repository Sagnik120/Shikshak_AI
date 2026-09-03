"""Grounding prompt formatting per detailed_design.md §6.1."""

from __future__ import annotations

from typing import List, Tuple
from modules.rag.src.models import RetrievedChunk, GroundedContext


def format_grounding_context_block(
    retrieved_chunks: List[RetrievedChunk],
    has_sufficient_context: bool = True,
    risk_level: str = "low"
) -> GroundedContext:
    """Format retrieved chunks into an authoritative grounding context block for the Explainer/Teacher agents.

    Follows the strict grounding prompt specification in detailed_design.md §6.1.
    """
    if risk_level == "no_document_context":
        formatted = (
            "SOURCE MATERIAL: [No source document was provided — topic-based teaching mode]\n\n"
            "Instructions:\n"
            "- Teach and explain this concept using authoritative, clear pedagogical general knowledge.\n"
            "- Do NOT fabricate citations, document excerpts, page numbers, or slide numbers.\n"
            "- Ground all technical explanations in standard, verified curriculum facts.\n"
            "- Output at the end: grounded_on: []"
        )
        return GroundedContext(
            formatted_prompt_context=formatted,
            candidate_chunk_ids=[],
            has_sufficient_context=False,
            risk_flag="no_document_context"
        )

    if not retrieved_chunks or not has_sufficient_context:
        formatted = (
            "SOURCE MATERIAL: [No high-confidence document excerpts found for this topic]\n\n"
            "Instructions:\n"
            "- Explain this concept using general knowledge.\n"
            "- You MUST explicitly label the explanation with: '[General knowledge, not from the uploaded document]'.\n"
            "- Output at the end: grounded_on: []"
        )
        return GroundedContext(
            formatted_prompt_context=formatted,
            candidate_chunk_ids=[],
            has_sufficient_context=False,
            risk_flag="low_context_fallback_to_general_knowledge"
        )

    chunk_blocks = []
    candidate_ids = []

    for chunk in retrieved_chunks:
        candidate_ids.append(chunk.chunk_id)
        meta_parts = []
        if chunk.section_title:
            meta_parts.append(f'Section: "{chunk.section_title}"')
        if chunk.page_or_slide is not None and chunk.page_or_slide > 0:
            meta_parts.append(f"Page/Slide: {chunk.page_or_slide}")

        meta_str = f" ({', '.join(meta_parts)})" if meta_parts else ""
        chunk_blocks.append(f"[{chunk.chunk_id}]{meta_str}\n{chunk.text}")

    context_body = "\n\n".join(chunk_blocks)

    formatted = (
        "You are teaching using ONLY the following source material. Each excerpt has an ID.\n\n"
        f"{context_body}\n\n"
        "Instructions:\n"
        "- Answer/explain using ONLY the information in the excerpts above.\n"
        "- If the excerpts do not contain enough information to fully answer, say so explicitly,\n"
        "  then you may supplement with general knowledge — but you MUST label that portion as\n"
        "  '[General knowledge, not from the uploaded document]'.\n"
        "- After your explanation, output a line: grounded_on: [<cited chunk IDs>]\n"
        "  listing only the chunk IDs you actually used. If none were used, output grounded_on: []"
    )

    return GroundedContext(
        formatted_prompt_context=formatted,
        candidate_chunk_ids=candidate_ids,
        has_sufficient_context=True,
        risk_flag=None if risk_level == "low" else "marginal_context_score"
    )
