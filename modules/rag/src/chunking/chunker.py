"""Structure-aware semantic chunker respecting section and slide boundaries.

Follows detailed_design.md §2:
- 300 token target, 500 max tokens, 15% overlap.
- Never splits across heading/slide boundaries.
- Min-chunk merge guard to prevent orphan trailing chunks.
"""

from __future__ import annotations

import re
import uuid
import logging
from typing import List, Optional, Any

from modules.rag.src.models import Chunk, RawSection

logger = logging.getLogger(__name__)

# Global cached tokenizer
_TOKENIZER = None


def get_tokenizer():
    """Retrieve or lazily initialize the BGE-M3 / HuggingFace tokenizer."""
    global _TOKENIZER
    if _TOKENIZER is not None:
        return _TOKENIZER
    try:
        from transformers import AutoTokenizer
        _TOKENIZER = AutoTokenizer.from_pretrained("BAAI/bge-m3")
        return _TOKENIZER
    except Exception:
        # Script-aware approximation tokenizer when offline/model not cached
        class SimpleApproximationTokenizer:
            def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
                # Indic (Devanagari/Bengali) words expand to ~2.4 subwords in BGE-M3/XLM-R
                # Latin/English words expand to ~1.3 tokens per word
                words = re.findall(r'\S+', text)
                total_tokens = 0.0
                for w in words:
                    has_indic = bool(re.search(r'[\u0900-\u097F\u0980-\u09FF]', w))
                    total_tokens += 2.4 if has_indic else 1.3
                n_tokens = max(1, int(total_tokens)) if words else 0
                return list(range(n_tokens))

            def decode(self, token_ids: list[int]) -> str:
                return ""

        _TOKENIZER = SimpleApproximationTokenizer()
        return _TOKENIZER


def count_tokens(text: str, tokenizer: Any = None) -> int:
    """Count tokens in string using tokenizer or script-aware subword expansion approximation."""
    if not text:
        return 0
    tok = tokenizer or get_tokenizer()
    try:
        return len(tok.encode(text, add_special_tokens=False))
    except Exception:
        words = re.findall(r'\S+', text)
        total_tokens = 0.0
        for w in words:
            has_indic = bool(re.search(r'[\u0900-\u097F\u0980-\u09FF]', w))
            total_tokens += 2.4 if has_indic else 1.3
        return max(1, int(total_tokens)) if words else 0


def split_text_into_token_chunks(
    text: str,
    target_tokens: int = 300,
    max_tokens: int = 500,
    overlap_pct: float = 0.15,
    min_chunk_tokens: int = 50,
    tokenizer: Any = None
) -> List[str]:
    """Split a single block of text into overlapping token chunks without splitting sentences.

    Guards:
    - If total tokens <= target_tokens, returns [text].
    - Merges trailing chunks < min_chunk_tokens into the previous chunk.
    """
    text = text.strip()
    if not text:
        return []

    tok = tokenizer or get_tokenizer()
    total_tokens = count_tokens(text, tok)

    if total_tokens <= target_tokens:
        return [text]

    # Split text into sentence units
    sentence_delimiters = re.compile(r'(?<=[.!?।\n])\s+')
    raw_sentences = sentence_delimiters.split(text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    if not sentences:
        return [text]

    overlap_tokens = int(target_tokens * overlap_pct)
    chunks: List[str] = []
    current_sentences: List[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = count_tokens(sent, tok)

        # If a single sentence exceeds max_tokens, split it by words
        if sent_tokens > max_tokens:
            words = sent.split()
            word_accum: List[str] = []
            for w in words:
                word_accum.append(w)
                if count_tokens(" ".join(word_accum), tok) >= target_tokens:
                    current_sentences.append(" ".join(word_accum))
                    chunks.append(" ".join(current_sentences))
                    # Retain overlap
                    current_sentences = []
                    word_accum = []
            if word_accum:
                current_sentences.append(" ".join(word_accum))
                current_tokens = count_tokens(" ".join(current_sentences), tok)
            continue

        if current_tokens + sent_tokens > max_tokens:
            # Finalize current chunk
            if current_sentences:
                chunk_str = " ".join(current_sentences).strip()
                chunks.append(chunk_str)

            # Build overlap from tail sentences
            overlap_accum: List[str] = []
            overlap_count = 0
            for prev_sent in reversed(current_sentences):
                p_tok = count_tokens(prev_sent, tok)
                if overlap_count + p_tok <= overlap_tokens:
                    overlap_accum.insert(0, prev_sent)
                    overlap_count += p_tok
                else:
                    break

            current_sentences = overlap_accum + [sent]
            current_tokens = count_tokens(" ".join(current_sentences), tok)
        else:
            current_sentences.append(sent)
            current_tokens += sent_tokens

    # Flush final accumulated chunk
    if current_sentences:
        final_chunk = " ".join(current_sentences).strip()
        final_tokens = count_tokens(final_chunk, tok)

        # Min-chunk-size guard: if trailing chunk < min_chunk_tokens, merge into previous
        # only if the combined text does not breach max_tokens
        if chunks and final_tokens < min_chunk_tokens:
            merged = f"{chunks[-1]} {final_chunk}".strip()
            if count_tokens(merged, tok) <= max_tokens:
                chunks[-1] = merged
            else:
                chunks.append(final_chunk)
        else:
            chunks.append(final_chunk)

    # Final ground-truth verification guard against subword budget overflow
    return finalize_and_verify_chunks(
        chunks=chunks,
        max_tokens=max_tokens,
        min_chunk_tokens=min_chunk_tokens,
        tokenizer=tok
    )


def finalize_and_verify_chunks(
    chunks: List[str],
    max_tokens: int = 500,
    min_chunk_tokens: int = 50,
    tokenizer: Any = None
) -> List[str]:
    """Ground-truth validation pass ensuring every emitted chunk strictly satisfies <= max_tokens.

    Guarantees Contract §4 chunk token budget even under heavy Indic conjunct expansion,
    code-mixed Hinglish, or trailing sentence merges.
    """
    if not chunks:
        return []

    tok = tokenizer or get_tokenizer()
    verified: List[str] = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        real_tokens = count_tokens(chunk, tok)
        if real_tokens <= max_tokens:
            verified.append(chunk)
        else:
            # Recursively subdivide chunk that exceeded max_tokens
            sentences = re.split(r'(?<=[.!?।\n])\s+', chunk)
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) > 1:
                mid = len(sentences) // 2
                part1 = " ".join(sentences[:mid]).strip()
                part2 = " ".join(sentences[mid:]).strip()
                verified.extend(
                    finalize_and_verify_chunks([part1, part2], max_tokens, min_chunk_tokens, tok)
                )
            else:
                # If a single sentence exceeds max_tokens, split on words
                words = chunk.split()
                mid = len(words) // 2
                part1 = " ".join(words[:mid]).strip()
                part2 = " ".join(words[mid:]).strip()
                verified.extend(
                    finalize_and_verify_chunks([part1, part2], max_tokens, min_chunk_tokens, tok)
                )

    return verified


def chunk_sections(
    sections: List[RawSection],
    document_id: str = "",
    target_tokens: int = 300,
    max_tokens: int = 500,
    overlap_pct: float = 0.15,
    tokenizer: Any = None
) -> List[Chunk]:
    """Structure-aware chunking over parsed RawSections.

    Never chunks across section/heading boundaries. Each section is chunked independently.
    Preserves section_title and page_or_slide metadata for citations.
    """
    tok = tokenizer or get_tokenizer()
    chunks: List[Chunk] = []
    chunk_counter = 1

    for section in sections:
        raw_text = section.raw_text.strip()
        if not raw_text:
            continue

        split_texts = split_text_into_token_chunks(
            raw_text,
            target_tokens=target_tokens,
            max_tokens=max_tokens,
            overlap_pct=overlap_pct,
            tokenizer=tok
        )

        for text_chunk in split_texts:
            chunk_id = f"chunk_{document_id[:8]}_{chunk_counter:04d}" if document_id else f"chunk_{chunk_counter:04d}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    text=text_chunk,
                    section_title=section.section_title,
                    page_or_slide=section.page_or_slide,
                    embedding_ref=""
                )
            )
            chunk_counter += 1

    return chunks
