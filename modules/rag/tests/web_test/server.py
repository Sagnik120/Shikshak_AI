"""Isolated Web Testbed Server for the RAG Module.

Runs on port 8002 independently of the production backend (port 8000).
Directly imports and tests modules.rag.src.* components.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import io
import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Direct imports from production RAG source code
from modules.rag.src.models import (
    ParsedDocument,
    Chunk,
    DetectedStructure,
    RetrievalResult,
    GroundedContext
)
from modules.rag.src.service import RAGService
from modules.rag.src.parsing.parser import parse_document, extract_raw_sections
from modules.rag.src.parsing.structure import detect_language, extract_key_terms_tfidf, normalize_indic_numerals
from modules.rag.src.chunking.chunker import chunk_sections, count_tokens, split_text_into_token_chunks
from modules.rag.src.embedding.factory import get_embedding_adapter
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.retrieval.retriever import HybridRetriever
from modules.rag.src.retrieval.rrf import reciprocal_rank_fusion
from modules.rag.src.retrieval.reranker import BGEReranker
from modules.rag.src.grounding.prompt import format_grounding_context_block
from modules.rag.src.grounding.extractor import parse_grounded_citations

# Structured Test Logger
from modules.rag.tests.web_test.logger import RAGTestLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_web_test_server")

# In-memory document cache for rapid browser testing
DOC_CACHE: Dict[str, ParsedDocument] = {}

# Initialize shared RAG Service instance
shared_vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
shared_embedding_adapter = get_embedding_adapter()
rag_service = RAGService(
    vector_store=shared_vector_store,
    embedding_adapter=shared_embedding_adapter
)

app = FastAPI(
    title="Shikshak AI — RAG Module Isolated Testbed",
    description="Standalone test harness for parsing, chunking, BGE-M3 embeddings, hybrid retrieval, and anti-hallucination verification.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Pre-load Verified Sample Documents
# ----------------------------------------------------------------------------
SAMPLE_PHYSICS = """Chapter 12: Electricity and Ohm's Law

12.1 Electric Current and Circuit
An electric current is expressed by the amount of charge flowing through a particular area in unit time. In other words, it is the rate of flow of electric charges. In circuits using metallic wires, electrons constitute the flow of charges.

12.2 Electric Potential and Potential Difference
Electric potential difference between two points in an electric circuit carrying some current is defined as the work done to move a unit charge from one point to the other.
Formula: V = W / Q. The SI unit of electric potential difference is volt (V), named after Alessandro Volta.

12.3 Ohm's Law
German physicist Georg Simon Ohm found that the electric current (I) flowing through a metallic wire is directly proportional to the potential difference (V) across its ends, provided its temperature remains constant.
Mathematical relationship: V = I * R, where R is a constant for the given metallic wire called its resistance. The SI unit of resistance is ohm (Ω).

12.4 Factors on which the Resistance of a Conductor Depends
Resistance of a uniform metallic conductor is directly proportional to its length (l) and inversely proportional to the area of cross-section (A).
Formula: R = ρ * (l / A), where ρ (rho) is the electrical resistivity of the material.
"""

SAMPLE_HINDI = """अध्याय 10: प्रकाश – परावर्तन तथा अपवर्तन

10.1 प्रकाश का परावर्तन
उच्च कोटि की पॉलिश किया हुआ पृष्ठ, जैसे कि दर्पण, अपने पर पड़ने वाले अधिकांश प्रकाश को परावर्तित कर देता है। प्रकाश के परावर्तन के दो नियम हैं:
(i) आपतन कोण, परावर्तन कोण के बराबर होता है।
(ii) आपतित किरण, दर्पण के आपतन बिंदु पर अभिलंब तथा परावर्तित किरण, ये सभी एक ही तल में होते हैं।

10.2 गोलीय दर्पण
ऐसे दर्पण जिनका परावर्तक पृष्ठ गोलीय है, गोलीय दर्पण कहलाते हैं। यदि परावर्तक पृष्ठ अंदर की ओर वक्रित हो, तो वह अवतल दर्पण (Concave Mirror) कहलाता है। यदि परावर्तक पृष्ठ बाहर की ओर वक्रित हो, तो वह उत्तल दर्पण (Convex Mirror) कहलाता है।
गोलीय दर्पण के ध्रुव (P) तथा मुख्य फोकस (F) के बीच की दूरी को फोकस दूरी (f) कहते हैं।
सूत्र: R = 2f, जहाँ R दर्पण के वक्रता केंद्र की त्रिज्या है।
"""

def _seed_samples():
    try:
        doc1 = rag_service.ingest_document(
            file_bytes=SAMPLE_PHYSICS.encode("utf-8"),
            filename="NCERT_Class10_Physics_Electricity.txt",
            mime_type="text/plain",
            document_id="doc_physics_ohm"
        )
        DOC_CACHE[doc1.document_id] = doc1

        doc2 = rag_service.ingest_document(
            file_bytes=SAMPLE_HINDI.encode("utf-8"),
            filename="NCERT_Class10_Hindi_Light.txt",
            mime_type="text/plain",
            document_id="doc_hindi_light"
        )
        DOC_CACHE[doc2.document_id] = doc2
    except Exception as e:
        logger.warning(f"Could not seed sample documents: {e}")

_seed_samples()

# ----------------------------------------------------------------------------
# API Schemas
# ----------------------------------------------------------------------------
class ParseTextRequest(BaseModel):
    raw_text: str = Field(..., description="Raw text content to parse")
    filename: str = Field("custom_notes.txt", description="Simulated filename")
    document_id: Optional[str] = Field(None, description="Optional custom document ID")

class ChunkTestRequest(BaseModel):
    text: str
    target_tokens: int = 300
    max_tokens: int = 500
    overlap_pct: float = 0.15

class EmbedTestRequest(BaseModel):
    texts: List[str]

class RetrievalTestRequest(BaseModel):
    document_id: Optional[str] = None
    query_text: str
    top_k: int = 5
    relevance_threshold: float = 0.5001
    confidence_threshold: float = 0.52

class GroundingAuditRequest(BaseModel):
    document_id: Optional[str] = None
    query_text: str
    simulated_teacher_response: Optional[str] = None
    top_k: int = 5
    relevance_threshold: float = 0.5001
    confidence_threshold: float = 0.52


# ----------------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------------

@app.get("/api/test/status")
def get_status():
    """System status and document cache manifest."""
    return {
        "service": "Shikshak AI — RAG Module Isolated Web Testbed",
        "port": 8002,
        "production_backend": "Untouched (Port 8000)",
        "embedding_adapter": type(shared_embedding_adapter).__name__,
        "vector_store": type(shared_vector_store).__name__,
        "cached_documents": [
            {
                "document_id": doc.document_id,
                "source_lang": doc.source_lang,
                "chunk_count": len(doc.chunks),
                "chapters": doc.detected_structure.chapters,
                "key_terms": doc.detected_structure.key_terms,
                "warnings": doc.warnings
            }
            for doc in DOC_CACHE.values()
        ]
    }


@app.post("/api/test/parse")
async def test_parse_document(
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    document_id: Optional[str] = Form(None)
):
    """Parse an uploaded file or raw text input into ParsedDocument (Contract §4)."""
    run = RAGTestLogger.start_run(
        category="parsing",
        source_file="modules/rag/src/parsing/parser.py",
        function_name="parse_document",
        input_payload={
            "has_file": bool(file),
            "filename": file.filename if file else filename or "pasted_text.txt",
            "text_length": len(raw_text or "")
        }
    )

    try:
        target_filename = file.filename if file else filename or "pasted_text.txt"
        mime_type = file.content_type if file and file.content_type else "text/plain"

        if file:
            file_bytes = await file.read()
        elif raw_text:
            file_bytes = raw_text.encode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="Either file upload or raw_text is required.")

        run.add_step("extract_raw_sections", {
            "file_bytes_size": len(file_bytes),
            "filename": target_filename,
            "mime_type": mime_type
        })

        # Ingest and index directly via production RAG service
        parsed_doc = rag_service.ingest_document(
            file_bytes=file_bytes,
            filename=target_filename,
            mime_type=mime_type,
            document_id=document_id
        )

        DOC_CACHE[parsed_doc.document_id] = parsed_doc

        output = {
            "document_id": parsed_doc.document_id,
            "source_lang": parsed_doc.source_lang,
            "chunk_count": len(parsed_doc.chunks),
            "chapters": parsed_doc.detected_structure.chapters,
            "key_terms": parsed_doc.detected_structure.key_terms,
            "warnings": parsed_doc.warnings,
            "chunks_sample": [
                {
                    "chunk_id": c.chunk_id,
                    "section_title": c.section_title,
                    "page_or_slide": c.page_or_slide,
                    "text": c.text,
                    "embedding_ref": c.embedding_ref
                }
                for c in parsed_doc.chunks[:10]
            ]
        }

        run.complete(output)
        return output

    except Exception as e:
        run.fail(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/chunk")
def test_chunking(req: ChunkTestRequest):
    """Test script-aware semantic chunking directly."""
    run = RAGTestLogger.start_run(
        category="chunking",
        source_file="modules/rag/src/chunking/chunker.py",
        function_name="split_text_into_token_chunks",
        input_payload=req.model_dump()
    )

    try:
        total_tokens = count_tokens(req.text)
        has_indic = bool(count_tokens(req.text) > len(req.text.split()) * 1.5)

        run.add_step("token_count_analysis", {
            "character_length": len(req.text),
            "word_count": len(req.text.split()),
            "estimated_tokens": total_tokens,
            "indic_multiplier_active": has_indic
        })

        raw_chunks = split_text_into_token_chunks(
            text=req.text,
            target_tokens=req.target_tokens,
            max_tokens=req.max_tokens,
            overlap_pct=req.overlap_pct
        )

        chunk_details = []
        for idx, text in enumerate(raw_chunks):
            tokens = count_tokens(text)
            chunk_details.append({
                "chunk_index": idx + 1,
                "token_count": tokens,
                "word_count": len(text.split()),
                "text": text,
                "satisfies_budget": tokens <= req.max_tokens
            })

        output = {
            "total_input_tokens": total_tokens,
            "total_chunks": len(raw_chunks),
            "chunks": chunk_details
        }

        run.complete(output)
        return output

    except Exception as e:
        run.fail(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/embed")
def test_embeddings(req: EmbedTestRequest):
    """Test dense and sparse embedding calculation."""
    run = RAGTestLogger.start_run(
        category="embedding",
        source_file="modules/rag/src/embedding/bge_m3.py",
        function_name="embed_passages",
        input_payload={"texts_count": len(req.texts)}
    )

    try:
        dense_vecs, sparse_weights = shared_embedding_adapter.embed_passages(req.texts)

        results = []
        for idx, (dense, sparse) in enumerate(zip(dense_vecs, sparse_weights)):
            top_sparse = sorted(sparse.items(), key=lambda x: x[1], reverse=True)[:10]
            results.append({
                "index": idx,
                "text_snippet": req.texts[idx][:80] + ("..." if len(req.texts[idx]) > 80 else ""),
                "dense_dimension": len(dense),
                "dense_sample": [round(x, 4) for x in dense[:8]],
                "sparse_terms_count": len(sparse),
                "top_sparse_terms": {k: round(v, 4) for k, v in top_sparse}
            })

        output = {
            "model": type(shared_embedding_adapter).__name__,
            "total_texts": len(req.texts),
            "results": results
        }

        run.complete(output)
        return output

    except Exception as e:
        run.fail(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/retrieve")
def test_retrieval(req: RetrievalTestRequest):
    """Test hybrid retrieval with dense + sparse + RRF + cross-encoder reranking."""
    run = RAGTestLogger.start_run(
        category="retrieval",
        source_file="modules/rag/src/retrieval/retriever.py",
        function_name="retrieve",
        input_payload=req.model_dump()
    )

    try:
        clean_doc_id = req.document_id.strip() if req.document_id and req.document_id not in ("topic_only", "none", "") else None

        run.add_step("query_dispatch", {
            "document_id": clean_doc_id,
            "is_topic_only": clean_doc_id is None,
            "query_text": req.query_text
        })

        result = rag_service.retrieve_context(
            document_id=clean_doc_id,
            query_text=req.query_text,
            top_k=req.top_k,
            relevance_threshold=req.relevance_threshold,
            confidence_threshold=req.confidence_threshold
        )

        formatted_chunks = [
            {
                "chunk_id": c.chunk_id,
                "section_title": c.section_title,
                "page_or_slide": c.page_or_slide,
                "reranker_score": round(c.score, 4),
                "dense_score": round(c.dense_score, 4) if c.dense_score is not None else None,
                "sparse_score": round(c.sparse_score, 4) if c.sparse_score is not None else None,
                "text": c.text
            }
            for c in result.chunks
        ]

        output = {
            "document_id": result.document_id,
            "query_text": result.query_text,
            "has_sufficient_context": result.has_sufficient_context,
            "risk_level": result.risk_level,
            "candidate_count": len(formatted_chunks),
            "candidates": formatted_chunks
        }

        if result.risk_level == "high_hallucination_risk":
            run.record_hallucination_risk(
                hallucinated_chunk_ids=[],
                empty_citations=False,
                source_file="modules/rag/src/retrieval/retriever.py",
                source_function="retrieve",
                message=f"Query scored below relevance threshold ({req.relevance_threshold}); flagged as out-of-scope."
            )

        run.complete(output)
        return output

    except Exception as e:
        run.fail(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test/grounding")
def test_grounding_and_audit(req: GroundingAuditRequest):
    """Test grounding prompt generation and audit teacher output for citations/hallucination."""
    run = RAGTestLogger.start_run(
        category="grounding",
        source_file="modules/rag/src/grounding/prompt.py",
        function_name="format_grounding_context_block",
        input_payload=req.model_dump()
    )

    try:
        clean_doc_id = req.document_id.strip() if req.document_id and req.document_id not in ("topic_only", "none", "") else None

        # 1. Retrieve context
        retrieval_result = rag_service.retrieve_context(
            document_id=clean_doc_id,
            query_text=req.query_text,
            top_k=req.top_k,
            relevance_threshold=req.relevance_threshold,
            confidence_threshold=req.confidence_threshold
        )

        # 2. Format Grounding Block
        grounded_context = format_grounding_context_block(
            retrieved_chunks=retrieval_result.chunks,
            has_sufficient_context=retrieval_result.has_sufficient_context,
            risk_level=retrieval_result.risk_level
        )

        run.add_step("grounded_context_generated", {
            "has_sufficient_context": grounded_context.has_sufficient_context,
            "risk_flag": grounded_context.risk_flag,
            "candidate_chunk_ids": grounded_context.candidate_chunk_ids
        })

        audit_result = {
            "clean_teacher_explanation": None,
            "cited_chunk_ids": [],
            "risk_signal": None,
            "is_hallucinating": False,
            "hallucination_source_file": None,
            "hallucination_source_function": None
        }

        # 3. Citation Audit if simulated response was provided
        if req.simulated_teacher_response:
            clean_text, cited_ids, risk_sig = parse_grounded_citations(
                llm_output_text=req.simulated_teacher_response,
                valid_candidate_ids=grounded_context.candidate_chunk_ids
            )
            is_hallucinating = bool(risk_sig)

            audit_result = {
                "clean_teacher_explanation": clean_text,
                "cited_chunk_ids": cited_ids,
                "risk_signal": risk_sig,
                "is_hallucinating": is_hallucinating,
                "hallucination_source_file": "modules/rag/src/grounding/extractor.py" if is_hallucinating else None,
                "hallucination_source_function": "parse_grounded_citations" if is_hallucinating else None
            }

            if is_hallucinating:
                run.record_hallucination_risk(
                    hallucinated_chunk_ids=[c for c in cited_ids if c not in set(grounded_context.candidate_chunk_ids)],
                    empty_citations=(not cited_ids and len(grounded_context.candidate_chunk_ids) >= 2),
                    source_file="modules/rag/src/grounding/extractor.py",
                    source_function="parse_grounded_citations",
                    message=f"Citation discrepancy detected: {risk_sig}"
                )

        output = {
            "prompt_context": grounded_context.formatted_prompt_context,
            "candidate_chunk_ids": grounded_context.candidate_chunk_ids,
            "has_sufficient_context": grounded_context.has_sufficient_context,
            "risk_flag": grounded_context.risk_flag,
            "citation_audit": audit_result
        }

        run.complete(output)
        return output

    except Exception as e:
        run.fail(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test/logs")
def list_logs(category: Optional[str] = None, limit: int = 50):
    """List structured diagnostic logs across categories."""
    return {
        "category": category or "all",
        "logs": RAGTestLogger.list_recent_logs(category=category, limit=limit)
    }


@app.get("/api/test/logs/{category}/{filename}")
def get_log_file(category: str, filename: str):
    """Retrieve full JSON log details."""
    detail = RAGTestLogger.get_log_detail(category=category, filename=filename)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Log file '{filename}' in category '{category}' not found.")
    return detail


# ----------------------------------------------------------------------------
# Mount Static UI Files
# ----------------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("  SHIKSHAK AI — RAG ISOLATED WEB TESTBED")
    print("  Running on: http://localhost:8002")
    print("  Testing Code: modules/rag/src/")
    print("  Production Backend (Port 8000) remains 100% untouched.")
    print("=" * 70)
    uvicorn.run(app, host="0.0.0.0", port=8002)
