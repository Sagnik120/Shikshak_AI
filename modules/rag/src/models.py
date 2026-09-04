"""Contract models and internal data structures for the RAG module.

Strictly adheres to ROOT `instructions/Contract.md` §4 and §14.
Internal extension types are flagged and documented per detailed_design.md §9.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# ROOT CONTRACT §4: ParsedDocument and related types
# MUST NOT deviate from instructions/Contract.md §4
# ============================================================================

class Chunk(BaseModel):
    """Chunk schema matching Contract §4."""
    chunk_id: str = Field(..., description="Unique identifier for the chunk, e.g. chunk_a1b2")
    text: str = Field(..., description="Raw text content of the chunk")
    section_title: Optional[str] = Field(None, description="Title of the section or slide heading if detected")
    page_or_slide: Optional[int] = Field(None, description="1-indexed page number (PDF) or slide number (PPTX)")
    embedding_ref: str = Field("", description="Reference identifier in the vector store")


class DetectedStructure(BaseModel):
    """Document structural metadata matching Contract §4."""
    chapters: List[str] = Field(default_factory=list, description="Detected chapter or high-level section titles")
    key_terms: List[str] = Field(default_factory=list, description="Top extracted keywords/keyphrases from the document")


class ParsedDocument(BaseModel):
    """Authoritative document representation produced by RAG module (Contract §4)."""
    document_id: str = Field(..., description="Unique document ID (UUID or hash)")
    source_lang: str = Field(..., description="Detected primary language (ISO 639-1, e.g. 'en', 'hi')")
    chunks: List[Chunk] = Field(default_factory=list, description="List of structured text chunks")
    detected_structure: DetectedStructure = Field(
        default_factory=DetectedStructure,
        description="Structural hierarchy and extracted key terms"
    )
    warnings: List[str] = Field(
        default_factory=list,
        exclude=True,
        description="Diagnostic warnings (e.g. scanned pages with near-zero text, OCR incomplete)"
    )


# ============================================================================
# INTERNAL / INTERMEDIATE TYPES (Not in Contract.md — RAG module internal)
# ============================================================================

class RawSection(BaseModel):
    """Internal representation of a parsed document section prior to chunking."""
    section_title: Optional[str] = None
    page_or_slide: Optional[int] = None
    raw_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# PROPOSED CONTRACT EXTENSIONS (detailed_design.md §9)
# Used internally and exposed for orchestration consumption
# ============================================================================

class RetrievedChunk(BaseModel):
    """Chunk returned by retrieval with relevance score and metadata."""
    chunk_id: str
    text: str
    section_title: Optional[str] = None
    page_or_slide: Optional[int] = None
    score: float = Field(..., description="Fused relevance score (RRF or reranker score)")
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None


class RetrievalRequest(BaseModel):
    """Query parameters for retrieving grounding context."""
    document_id: Optional[str] = Field(default=None, description="Document ID or None for topic-only teaching")
    query_text: str
    top_k: int = Field(default=5, ge=1, le=50)
    relevance_threshold: float = Field(default=0.2, description="Minimum reranker score for grounding")


class RetrievalResult(BaseModel):
    """Result of retrieval operation."""
    document_id: Optional[str] = Field(default=None, description="Document ID or None for topic-only teaching")
    query_text: str
    chunks: List[RetrievedChunk] = Field(default_factory=list)
    has_sufficient_context: bool = Field(
        default=True,
        description="False if all retrieved candidates are below relevance threshold or no document provided"
    )
    risk_level: str = Field(
        default="low",
        description="'low', 'no_document_context', or 'high_hallucination_risk'"
    )

    @property
    def candidate_chunks(self) -> List[RetrievedChunk]:
        """Convenience alias for chunks."""
        return self.chunks


class GroundedContext(BaseModel):
    """Formatted grounding context block to inject into AI Teacher prompts."""
    formatted_prompt_context: str
    candidate_chunk_ids: List[str]
    has_sufficient_context: bool
    risk_flag: Optional[str] = None
