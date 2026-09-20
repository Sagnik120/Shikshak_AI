"""ChromaDB implementation of VectorStoreAdapter.

Production optimizations:
- Inverted index for O(M·k) sparse lookup (replaces O(N·M) linear scan)
- IDF-weighted BM25-style sparse scoring
"""

from __future__ import annotations

import os
import math
import json
import logging
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple, Set

from modules.rag.src.models import Chunk
from modules.rag.src.indexing.vector_store_adapter import VectorStoreAdapter

logger = logging.getLogger(__name__)


class ChromaVectorStoreAdapter(VectorStoreAdapter):
    """Chroma implementation of the vector store adapter."""

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
        self._client = None
        self._sparse_store: Dict[str, Dict[str, Dict[str, float]]] = {}  # doc_id -> chunk_id -> sparse_dict
        self._chunk_lookup: Dict[str, Dict[str, Chunk]] = {}  # doc_id -> chunk_id -> Chunk
        # Inverted index: doc_id -> term -> set of chunk_ids containing that term
        self._inverted_index: Dict[str, Dict[str, Set[str]]] = {}
        # Document frequency: doc_id -> term -> number of chunks containing the term
        self._doc_freq: Dict[str, Dict[str, int]] = {}
        # Total chunk count per document (for IDF calculation)
        self._doc_chunk_count: Dict[str, int] = {}

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import chromadb
            if self.persist_dir == ":memory:":
                self._client = chromadb.EphemeralClient()
            else:
                os.makedirs(self.persist_dir, exist_ok=True)
                self._client = chromadb.PersistentClient(path=self.persist_dir)
            return self._client
        except Exception as e:
            logger.warning(f"Could not initialize ChromaDB client ({e}). Using in-memory fallback.")
            self._client = "mock"
            return self._client

    def _get_collection(self, document_id: str):
        client = self._get_client()
        if client == "mock":
            return None
        safe_name = f"doc_{document_id.replace('-', '_')}"
        return client.get_or_create_collection(
            name=safe_name,
            metadata={"hnsw:space": "cosine"}
        )

    def upsert(
        self,
        document_id: str,
        chunks: List[Chunk],
        dense_embeddings: List[List[float]],
        sparse_weights: Optional[List[Dict[str, float]]] = None
    ) -> List[str]:
        if not chunks:
            return []

        if document_id not in self._sparse_store:
            self._sparse_store[document_id] = {}
        if document_id not in self._chunk_lookup:
            self._chunk_lookup[document_id] = {}

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "section_title": c.section_title or "",
                "page_or_slide": c.page_or_slide if c.page_or_slide is not None else -1,
                "document_id": document_id
            }
            for c in chunks
        ]

        # Initialize inverted index structures for this document if needed
        if document_id not in self._inverted_index:
            self._inverted_index[document_id] = defaultdict(set)
            self._doc_freq[document_id] = defaultdict(int)
            self._doc_chunk_count[document_id] = 0

        # Store in internal lookups and build inverted index
        for idx, chunk in enumerate(chunks):
            self._chunk_lookup[document_id][chunk.chunk_id] = chunk
            chunk.embedding_ref = f"{document_id}#{chunk.chunk_id}"
            self._doc_chunk_count[document_id] += 1
            if sparse_weights and idx < len(sparse_weights):
                sw = sparse_weights[idx]
                self._sparse_store[document_id][chunk.chunk_id] = sw
                # Update inverted index and document frequency
                for term in sw:
                    if chunk.chunk_id not in self._inverted_index[document_id][term]:
                        self._inverted_index[document_id][term].add(chunk.chunk_id)
                        self._doc_freq[document_id][term] += 1

        # Upsert into Chroma collection if available
        collection = self._get_collection(document_id)
        if collection is not None:
            try:
                collection.upsert(
                    ids=ids,
                    embeddings=dense_embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
            except Exception as e:
                logger.error(f"Failed to upsert chunks into ChromaDB: {e}")

        return [c.embedding_ref for c in chunks]

    def query_dense(
        self,
        document_id: str,
        query_embedding: List[float],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection(document_id)
        if collection is not None:
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, collection.count() or 1),
                    include=["documents", "metadatas", "distances"]
                )
                matches: List[Dict[str, Any]] = []
                if results and results.get("ids") and results["ids"][0]:
                    ids = results["ids"][0]
                    docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
                    metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
                    distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

                    for c_id, text, meta, dist in zip(ids, docs, metas, distances):
                        # Cosine distance to similarity: 1 - distance
                        sim_score = max(0.0, 1.0 - float(dist))
                        matches.append({
                            "chunk_id": c_id,
                            "text": text,
                            "section_title": meta.get("section_title") or None,
                            "page_or_slide": meta.get("page_or_slide") if meta.get("page_or_slide", -1) != -1 else None,
                            "score": sim_score
                        })
                return matches
            except Exception as e:
                logger.error(f"Chroma dense query failed: {e}")

        # Fallback memory lookup
        doc_chunks = self._chunk_lookup.get(document_id, {})
        return [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "section_title": c.section_title,
                "page_or_slide": c.page_or_slide,
                "score": 0.5
            }
            for c in list(doc_chunks.values())[:top_k]
        ]

    def query_sparse(
        self,
        document_id: str,
        query_sparse: Dict[str, float],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Query sparse index using inverted index for O(M·k) lookup.

        Uses IDF-weighted scoring: score = Σ (q_weight × tf × idf)
        where idf = log(N / df) and N = total chunks in document.
        """
        inv_idx = self._inverted_index.get(document_id, {})
        doc_sparse = self._sparse_store.get(document_id, {})
        doc_chunks = self._chunk_lookup.get(document_id, {})
        if not inv_idx or not query_sparse:
            return []

        total_chunks = max(self._doc_chunk_count.get(document_id, 1), 1)
        df_map = self._doc_freq.get(document_id, {})

        # Accumulate scores using inverted index (only touch relevant chunks)
        scores: Dict[str, float] = {}
        for term, q_weight in query_sparse.items():
            posting_list = inv_idx.get(term)
            if not posting_list:
                continue
            # IDF: log(N / df), clamped to >= 0.1 for very common terms
            df = df_map.get(term, 1)
            idf = max(0.1, math.log(total_chunks / df))
            for chunk_id in posting_list:
                tf = doc_sparse.get(chunk_id, {}).get(term, 0.0)
                scores[chunk_id] = scores.get(chunk_id, 0.0) + (q_weight * tf * idf)

        # Sort by score descending and take top_k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for c_id, score in sorted_results:
            chunk = doc_chunks.get(c_id)
            if chunk:
                results.append({
                    "chunk_id": c_id,
                    "text": chunk.text,
                    "section_title": chunk.section_title,
                    "page_or_slide": chunk.page_or_slide,
                    "score": score
                })

        return results

    def query(
        self,
        embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Standard Contract §14 query implementation."""
        if not document_id:
            # If no document_id given, check first available
            keys = list(self._chunk_lookup.keys())
            if not keys:
                return []
            document_id = keys[0]

        return self.query_dense(document_id, embedding, top_k=top_k)
