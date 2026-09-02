"""Shikshak AI — RAG Module.

Exports Contract.md §4 compliant ParsedDocument, models, parsers, and RAGService.
"""

from modules.rag.src.models import (
    ParsedDocument,
    Chunk,
    DetectedStructure,
    RawSection,
    RetrievedChunk,
    RetrievalRequest,
    RetrievalResult,
    GroundedContext
)
from modules.rag.src.parsing.parser import parse_document, extract_raw_sections
from modules.rag.src.chunking.chunker import chunk_sections
from modules.rag.src.embedding.factory import get_embedding_adapter
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.retrieval.retriever import HybridRetriever
from modules.rag.src.grounding.prompt import format_grounding_context_block
from modules.rag.src.grounding.extractor import parse_grounded_citations
from modules.rag.src.service import RAGService

__all__ = [
    "ParsedDocument",
    "Chunk",
    "DetectedStructure",
    "RawSection",
    "RetrievedChunk",
    "RetrievalRequest",
    "RetrievalResult",
    "GroundedContext",
    "parse_document",
    "extract_raw_sections",
    "chunk_sections",
    "get_embedding_adapter",
    "ChromaVectorStoreAdapter",
    "HybridRetriever",
    "format_grounding_context_block",
    "parse_grounded_citations",
    "RAGService",
]
