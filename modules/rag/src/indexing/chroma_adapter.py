"""ChromaDB implementation of VectorStoreAdapter."""

from __future__ import annotations

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

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

        # Store in internal lookups
        for idx, chunk in enumerate(chunks):
            self._chunk_lookup[document_id][chunk.chunk_id] = chunk
            chunk.embedding_ref = f"{document_id}#{chunk.chunk_id}"
            if sparse_weights and idx < len(sparse_weights):
                self._sparse_store[document_id][chunk.chunk_id] = sparse_weights[idx]

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
        doc_sparse = self._sparse_store.get(document_id, {})
        doc_chunks = self._chunk_lookup.get(document_id, {})
        if not doc_sparse or not query_sparse:
            return []

        scored: List[Tuple[str, float]] = []
        for chunk_id, term_weights in doc_sparse.items():
            # Dot product of sparse lexical vectors
            dot = 0.0
            for term, q_weight in query_sparse.items():
                if term in term_weights:
                    dot += q_weight * term_weights[term]
            if dot > 0.0:
                scored.append((chunk_id, dot))

        scored.sort(key=lambda x: x[1], reverse=True)
        top_matches = scored[:top_k]

        results = []
        for c_id, score in top_matches:
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
