# detailed_design.md — RAG Module Implementation Guide (Shikshak AI)

**Module:** `modules/rag/`
**Owner:** RAG engineer(s)
**Consumes:** `UploadRequest`, raw file bytes
**Produces:** `ParsedDocument` (Contract §4) → consumed by `ai_agent_orchestration`
**Rubric weight:** 15/100 direct ("RAG & Knowledge Grounding"), contributes to 15/100 "AI/ML & LLM Implementation"
**Status:** Implementation-ready. All schemas below match `instructions/Contract.md` exactly — no field renamed, none added without being listed under "Proposed Contract Additions."

---

## 0. Sources this design is drawn from (not generic "RAG best practices")

| # | Source | What we take from it |
|---|--------|----------------------|
| 1 | **BGE-M3** (Chen et al., 2024, BAAI, HF: `BAAI/bge-m3`) | A single model that natively produces **dense + sparse (lexical) + ColBERT-style multi-vector** embeddings in one forward pass, over **100+ languages**, up to 8192 tokens. This is the core justification for using one model to do both semantic and keyword-style matching instead of standing up a separate BM25 stack *and* a separate dense encoder — critical for hackathon time budget. |
| 2 | **BGE-reranker-v2-m3** (HF: `BAAI/bge-reranker-v2-m3`) | Cross-encoder reranker, multilingual, used as the second-stage reranking step after first-stage dense/sparse retrieval — standard "retrieve-then-rerank" pattern reported across BGE-M3 production deployments. |
| 3 | **Multilingual-E5-large** (Wang et al., MSR-TR-2024-45, HF: `intfloat/multilingual-e5-large`) | Fallback/alternative embedding model (90+ languages, 1024-dim) if BGE-M3's dependency footprint (FlagEmbedding) is too heavy for the hackathon environment. Documented here as the swap-in option behind `VectorStoreAdapter`/embedding config, not a second pipeline. |
| 4 | **RAGAS** (Es et al., 2023, *"RAGAs: Automated Evaluation of Retrieval Augmented Generation"*, arXiv:2309.15217) | Reference-free **faithfulness** metric: decompose a generated answer into atomic claims, check each claim is entailed by the retrieved chunks. We reuse this exact decomposition technique for the module's own groundedness test harness, without pulling in the full RAGAS dependency — reimplemented as a small entailment-check function. |
| 5 | **"Grounded in Context" pattern** (Deepchecks RAG eval writeup, arXiv:2605.14488) | Same claim-decomposition-and-entailment idea as RAGAS, confirms this is a converging standard, not a one-off — used to justify our groundedness test design in §7. |
| 6 | **SelfCheckGPT** (Manakul et al., 2023) style self-consistency idea | Not implemented directly (too slow for hackathon — needs N generations per answer), but its core insight — *disagreement across resampled generations signals ungrounded content* — informs a cheap fallback: if the LLM's `grounded_on` self-report is empty on a query with non-trivial retrieved context, treat this as a mild hallucination-risk signal (see §6.3), rather than building a full self-consistency system.
| 7 | **LlamaIndex `SentenceWindowNodeParser` / hierarchical node parser patterns** | Source of the "parse structure first, chunk within structure, don't chunk across heading boundaries" approach used in §2. We don't adopt LlamaIndex as a hard dependency (Contract already leaves this open) but we adopt its chunking *strategy*, implementable directly with `pypdf`/`python-docx`/`python-pptx` + a custom splitter — lighter than pulling in the whole framework for a hackathon.
| 8 | **Chroma** (open-source, embedded, no server needed) | Chosen vector store, matches `02_Architecture.md`'s explicit suggestion ("Chroma for local/hackathon"), wrapped by `VectorStoreAdapter` per Contract §14 so Qdrant/Pinecone is a one-file swap later. |
| 9 | **BM25** (`rank_bm25` Python package, Robertson & Zaragoza's Okapi BM25) | Classic lexical scorer, used as an extra hybrid signal on top of BGE-M3's own sparse vector, cheap to add (~30 lines), particularly valuable for exact-term lookups (formula names, defined terms) that dense embeddings sometimes miss. |
| 10 | **HyDE** (Gao et al., 2022, *"Precise Zero-Shot Dense Retrieval without Relevance Labels"*) | Considered and explicitly **rejected** for MVP (see §8) — noted here because a juror familiar with RAG literature will expect it to be addressed. |

---

## 1. Component: Parsing

**Ownership decision (resolves an explicit open question in `detail_plan.md` step 1):**
> **Assumption/decision:** `rag` module **owns parsing**, not `ml_core`. Rationale: `ParsedDocument` is the RAG module's own output contract, chunking is structure-dependent, and duplicating a second parser in `ml_core` risks divergent chunk boundaries. `ml_core` is assumed to consume `ParsedDocument.chunks` / `detected_structure` for concept/entity extraction rather than re-parsing raw files. **This assumption should be confirmed with the ml_core owner before build — flagged explicitly per instructions.**

### Function signature
```python
def parse_document(file_bytes: bytes, filename: str, mime_type: str) -> ParsedDocument:
    """
    Input:  raw uploaded file bytes + filename/mime (from UploadRequest.file)
    Output: ParsedDocument (Contract §4) — exact shape, no extra top-level keys
    """
```

### Libraries per format
| Format | Library | Notes |
|---|---|---|
| PDF (text) | `pypdf` (or `pdfplumber` for better layout/table fidelity) | Extract text per page; capture page number for `page_or_slide`. |
| PDF (scanned/image-only) | `pytesseract` + `pdf2image` (poppler) | See edge case §5.1. |
| DOCX | `python-docx` | Walk `document.paragraphs`, use `style.name` starting with `Heading` to detect section boundaries → `section_title`. |
| PPTX | `python-pptx` | One "page_or_slide" per slide; concatenate all text frames per slide; slide title placeholder → `section_title`. |
| Plain notes (.txt/.md) | stdlib | Split on Markdown headings (`#`, `##`) if present, else fall back to paragraph-based chunking. |

### `detected_structure` extraction
- `chapters`: collected from Heading-1/Heading-2 styles (DOCX), slide titles (PPTX), or font-size-based heuristic on PDFs (largest, bolded, short lines = headings — cheap heuristic, not ML).
- `key_terms`: run a lightweight noun-phrase / TF-IDF top-N extraction (`sklearn.feature_extraction.text.TfidfVectorizer` on the whole doc) — no need for a heavy NER model at hackathon scope; flagged as an assumption below.

**Assumption flagged:** the rough plan didn't specify how `key_terms` should be produced. We assume TF-IDF top-N (cheap, deterministic, no extra model) is acceptable for hackathon scope rather than a trained NER/keyphrase model. If `ml_core` already owns a keyphrase extractor, this should be reconciled to avoid duplicate work.

---

## 2. Component: Chunking (structure-aware, not fixed-token)

### Strategy
1. Never chunk across a detected heading/slide boundary — each "section" (between two headings, or one slide) is chunked independently.
2. Within a section: recursive character/token splitter, **target 300 tokens, max 500 tokens, 15% overlap (≈45–75 tokens)** — chosen as the middle of the "~200–500 tokens" range in `detail_plan.md`, biased toward the smaller end because BGE-M3, while supporting 8192 tokens, retrieves more precisely with shorter, single-concept chunks (better recall@k for definition/formula lookups, per BGE-M3 usage notes in source #1).
3. If a section itself is shorter than 300 tokens (common for slide bullets), keep it as a single chunk rather than padding — avoids meaningless overlap chunks.
4. If a section has no natural heading (source #7's fallback case), fall back to sliding-window token chunking with the same 300/500/15% parameters, section_title = `null`.
5. Tokenizer for length counting: use BGE-M3's own tokenizer (`AutoTokenizer.from_pretrained("BAAI/bge-m3")`) so chunk-length budgeting matches what the embedding model actually sees, not a generic `tiktoken` count.

### Function signature
```python
def chunk_sections(sections: list[Section], tokenizer) -> list[Chunk]:
    """
    sections: internal intermediate type (not in Contract) — 
              {section_title, page_or_slide, raw_text}
    returns:  list of Chunk dicts matching Contract §4 chunks[] shape:
              {chunk_id, text, section_title, page_or_slide, embedding_ref}
              (embedding_ref populated in the embedding step, not here — set to null initially)
    """
```

---

## 3. Component: Embedding

### Model
**Primary:** `BAAI/bge-m3` via the `FlagEmbedding` library (`BGEM3FlagModel`), run locally (CPU-ok for hackathon-scale corpora, GPU if available). Produces dense (1024-dim) + sparse (lexical weight dict) + optionally ColBERT multi-vector output in one call — we use **dense + sparse only** for MVP (skip ColBERT multi-vector to save complexity/latency; see §8).

**Fallback (if `FlagEmbedding` install fails in the hackathon environment / time-boxed):** `intfloat/multilingual-e5-large` via `sentence-transformers`, dense-only, paired with a separate `rank_bm25` sparse index (source #9) to still get hybrid retrieval. This fallback path must be config-switchable, not a code fork — implement both behind one `EmbeddingAdapter`-style internal interface (this sits *inside* the `VectorStoreAdapter`/embedding step, distinct from the Contract's adapters, so no Contract change needed).

### Function signature
```python
def embed_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """
    Input: chunks with text, missing embedding_ref
    Output: same chunks, embedding_ref populated (points to vector store entry id)
    Side effect: writes dense+sparse vectors into Chroma via VectorStoreAdapter.upsert()
    """
```

E5 models require the `"query: "` / `"passage: "` prefix convention on inputs (per source #3/#13) — **only relevant if the E5 fallback path is used**; BGE-M3 does not require this prefixing.

---

## 4. Component: Indexing

- **Store:** Chroma, embedded/local mode (`chromadb.PersistentClient`), one collection per `document_id`. Matches `02_Architecture.md`'s explicit hackathon recommendation.
- Each vector record stores: `chunk_id`, dense embedding, sparse term-weights (as Chroma metadata or a parallel lightweight structure if Chroma's native sparse support is insufficient — fallback: keep BM25/sparse index as a separate in-memory `rank_bm25.BM25Okapi` object keyed by `chunk_id`, rather than fighting Chroma's API under time pressure), plus metadata: `section_title`, `page_or_slide`, `source_lang`.
- Wrapped behind `VectorStoreAdapter.upsert(chunks)` / `.query(embedding, top_k)` **exactly per Contract §14** — swapping to Qdrant/Pinecone later is a config change only.

---

## 5. Component: Retrieval

### Strategy — hybrid dense + sparse + rerank
1. Embed the query with the same model used for the corpus (BGE-M3 dense + sparse, or E5 dense + BM25 in fallback mode).
2. Retrieve **top 20** candidates by dense cosine similarity, **top 20** by sparse/BM25 score.
3. Fuse via **Reciprocal Rank Fusion (RRF)** (simple, parameter-light, no weight-tuning needed under time pressure — preferred here over hand-tuned linear weighting of dense/sparse scores): `score(chunk) = Σ 1/(60 + rank_in_list)`.
4. Take fused top 10, rerank with **`BAAI/bge-reranker-v2-m3`** cross-encoder (source #2), keep **top-k = 5** for the Explainer Agent's grounding context.
5. If a query needs cross-lingual retrieval (English textbook, Hindi teaching instruction) — no special-casing needed: BGE-M3's shared multilingual embedding space handles this natively per source #1's cross-lingual retrieval claim (validated on MIRACL/MKQA per source #15). This directly satisfies PS §8's "English textbook → Hindi teaching" requirement at the retrieval layer.

### What "query" means here
The RAG module doesn't receive a `StudentResponse`/free-text query directly per the Contract — retrieval is invoked internally whenever `ai_agent_orchestration` needs to ground a `LessonNode.concept` or an `InteractionEvent`. The retrieval query string is constructed by the caller (Explainer/Questioner agent) from the concept name; **the exact call shape into `rag` is not yet defined in Contract** — flagged in §9.

### Function signature (internal, called by orchestration layer)
```python
def retrieve(query_text: str, document_id: str, top_k: int = 5) -> list[RetrievedChunk]:
    """
    RetrievedChunk (internal type, proposed for Contract — see §9):
      {chunk_id, text, section_title, page_or_slide, score}
    """
```

---

## 6. Component: Grounding / Citation & Hallucination Mitigation

### 6.1 Prompt pattern (given to the Explainer/Questioner agent, RAG module supplies the context block)
```
You are teaching using ONLY the following source material. Each excerpt has an ID.

[chunk_a1b2] (Section: "Ohm's Law", Page 4)
<chunk text>

[chunk_c3d4] (Section: "Ohm's Law", Page 5)
<chunk text>

Instructions:
- Answer/explain using ONLY the information in the excerpts above.
- If the excerpts do not contain enough information to fully answer, say so explicitly,
  then you may supplement with general knowledge — but you MUST label that portion as
  "[General knowledge, not from the uploaded document]".
- After your explanation, output a line: grounded_on: [chunk_a1b2, chunk_c3d4]
  listing only the chunk IDs you actually used. If none were used, output grounded_on: []
```
This is the standard "context-restricted answer + explicit insufficient-context fallback + explicit general-knowledge labeling" pattern reflected across the grounding/faithfulness literature reviewed (sources #4, #5, #21) — the key idea being that ungrounded content should be *surfaced as such*, not silently blended in, which is exactly what PS §17 mandatory requirement 1 and the PRD's "RAG-grounded minimization, with citations" language require.

### 6.2 Citation propagation
The RAG module returns `grounded_on` chunk IDs alongside retrieved chunks so the UI can eventually show "based on Chapter 4." **This requires a small Contract addition** — `TeachingSegment` currently has no field for it. Listed formally in §9, not assumed silently.

### 6.3 Hallucination-risk signal (cheap SelfCheckGPT-inspired heuristic, source #6)
Rather than full self-consistency sampling (too slow/costly for hackathon), the RAG module flags a segment as **risk: low-context** whenever:
- top fused-and-reranked chunk score < a threshold (e.g. reranker score < 0.2), OR
- the agent's own `grounded_on` list comes back empty despite retrieval returning non-empty candidates.
This flag is surfaced to `AdaptationDecision` reasoning (already a Contract-defined mechanism — `HUMAN`/`REGENERATE` action with a `reason` string), so no new Contract field is needed there; it's a valid reuse of the existing `reason: string` field.

---

## 7. Testing (per component)

| Component | Test case | Expected behavior |
|---|---|---|
| Parsing | Upload a scanned image-only PDF (no text layer) | Falls back to OCR path; if OCR confidence low, `ParsedDocument.chunks` still populated but flagged internally (see §5.1); never silently returns empty chunks without signaling. |
| Parsing | DOCX with no heading styles at all | `detected_structure.chapters == []`, chunker falls back to sliding-window mode, no crash. |
| Parsing | 1-paragraph "document" (very short upload) | Single chunk produced, no forced overlap chunks; retrieval top_k gracefully capped at available chunk count. |
| Chunking | Section exactly 301 tokens | Confirms boundary logic doesn't create a near-empty trailing chunk (min-chunk-size guard, e.g. merge trailing chunk < 50 tokens into previous). |
| Embedding | Mixed-language document (English text, Hindi captions) | Both spans embed into the same space; a Hindi query retrieves the relevant English chunk and vice versa (cross-lingual retrieval test using MIRACL-style query/chunk pairs as informal sanity check, not full benchmark). |
| Retrieval | Query with no relevant chunks in corpus (e.g. asking about "black holes" on a Chapter-4-electricity doc) | Reranker scores all candidates low; system triggers the "insufficient context, falling back to general knowledge" prompt branch rather than fabricating a citation. |
| Grounding | LLM output claims a fact not present in any retrieved chunk | Groundedness test harness (RAGAS-style claim decomposition, source #4/#5) flags entailment failure; used as a CI-style check in `tests/eval/`, not a runtime blocker (runtime blocker would need an extra LLM call per teaching turn — noted as a nice-to-have, not MVP). |
| End-to-end | English textbook uploaded, "teach in Hindi" constraint | Retrieval still hits correct English chunks; Explainer Agent (outside this module) generates Hindi explanation citing those chunk IDs — validates the PS §8 explicit scenario. |

---

## 5.1 Edge cases (explicit, as required)

- **Scanned/image-only PDF:** detect via near-zero extractable text length relative to page count → route through `pytesseract` OCR. If OCR mean confidence is low (e.g. `pytesseract.image_to_data` avg conf < 40), still produce chunks but this is a case where downstream `ai_agent_orchestration` should be told confidence is low — **no Contract field currently carries this**; recommend logging only for MVP rather than blocking (see §9 for the optional addition).
- **Multilingual documents (mixed within one file):** `source_lang` at `ParsedDocument` level becomes a best-effort majority-language detection (`langdetect` or `fasttext` lang-id, cheap); chunk-level language is not separately tracked in the Contract's `ParsedDocument.chunks[]` shape — acceptable since BGE-M3 retrieval doesn't require per-chunk language tagging to work cross-lingually.
- **Very short uploads (<1 chunk worth of content):** single chunk, retrieval `top_k` silently clamped to available chunk count (no error), Explainer Agent context is just "the whole document."
- **No clear structure (wall-of-text PDF, no headings):** sliding-window fallback per §2 step 4; `detected_structure.chapters = []` is a valid, expected output, not an error state.
- **Retrieval returns nothing above a relevance floor:** triggers the explicit "insufficient context, falling back to general knowledge" branch in the prompt (§6.1) — this is the PRD's stated non-goal-adjacent requirement ("NOT guaranteeing zero hallucination — goal is RAG-grounded minimization, with citations") handled honestly rather than papered over.

---

## 8. Why this approach, not alternatives

- **BGE-M3 over separate dense-encoder + standalone BM25 stack:** one model call gets both signals, halving implementation and inference-latency surface — directly protects hackathon build time while still satisfying the "hybrid retrieval (dense + keyword)" ask; separate BM25 (`rank_bm25`) is kept only as a zero-cost fallback in the non-BGE-M3 path, not as mandatory extra infra.
- **Structure-aware chunking over fixed-token windows:** fixed windows routinely split a definition from its explanation, which directly hurts the "RAG & Knowledge Grounding" (15 pts) score by producing citations that don't actually contain the full claim — structure-aware chunking is a rubric-relevant choice, not just cleanliness.
- **RRF fusion over hand-tuned dense/sparse weighting:** RRF needs no tuning dataset (none exists yet at hackathon time), degrades gracefully, and is the standard choice reported alongside BGE-M3 pipelines (source #1 mentions this general "retrieve-then-rerank" fusion+cross-encoder pattern).
- **HyDE — explicitly rejected for MVP:** HyDE (source #10) improves recall on vague queries by generating a hypothetical answer first and embedding that, but it (a) requires an extra LLM call per retrieval — adds cost/latency to every teaching turn — and (b) can hurt precision when the hypothetical answer itself hallucinates, which is exactly the failure mode this module exists to prevent (confirmed by source #19's caution about HyDE). Given lesson-node concepts are already fairly well-specified strings (not vague user queries), the recall gain doesn't justify the risk here. Worth revisiting as an "Advanced Feature" if time remains.
- **Claim-decomposition groundedness checks (RAGAS/Deepchecks-style) over full self-consistency (SelfCheckGPT) at runtime:** SelfCheckGPT-style multi-sample consistency needs several extra generations per check — too slow/costly to run on every teaching turn in a live demo; instead we use the cheap `grounded_on` self-report + score-threshold heuristic at runtime (§6.3), and reserve the heavier claim-decomposition entailment check for offline `tests/eval/` groundedness testing where latency doesn't matter.
- **Chroma over Qdrant/Pinecone for hackathon:** zero infra setup, in-process, matches `02_Architecture.md`'s own explicit recommendation; `VectorStoreAdapter` makes the swap a config change, so this isn't a lock-in.

---

## 9. Proposed Contract Additions (NOT assumed into the design above — for review only)

1. **`TeachingSegment.grounded_on: list[string] | null`** — chunk IDs the Explainer Agent actually cited, so the frontend/right-panel can eventually show "based on Chapter 4." Currently `TeachingSegment` (Contract §6) has no field to carry this.
2. **A defined call/response shape between `ai_agent_orchestration` and `rag` for retrieval-on-demand** (e.g. `RetrievalRequest {document_id, query_text, top_k}` → `RetrievalResult {chunks: [{chunk_id, text, section_title, page_or_slide, score}]}`). The Contract currently defines `ParsedDocument` (RAG's output at ingestion time) but not the per-turn retrieval call orchestration makes while teaching — this module assumes such a call exists (§5) but its shape isn't in `Contract.md` today.
3. **Optional: `ParsedDocument.chunks[].ocr_confidence: number | null`** and/or a document-level `parse_quality_flag` — to let orchestration decide whether to surface a "this document was hard to read, results may be less reliable" notice (relevant to the scanned-PDF edge case in §5.1). Not required for MVP; nice-to-have if `HUMAN` escalation should ever trigger on parse quality.

None of the above are treated as adopted — they require sign-off and a version bump per `Contract.md`'s versioning section before any module codes against them.

---

## 10. Ambiguities / assumptions summary (all flagged inline above, collected here)

1. **Parsing ownership** assumed to belong to `rag`, not `ml_core` — needs cross-team confirmation.
2. **`key_terms` extraction method** assumed to be TF-IDF top-N, not a trained keyphrase/NER model — flagged as a possible duplicate-effort point with `ml_core`.
3. **Retrieval call shape between orchestration and rag** is assumed/invented at a reasonable interface but is **not yet in Contract.md** — listed formally under Proposed Contract Additions rather than silently built.
4. **`grounded_on` citation field** does not exist in the current `TeachingSegment` schema — the design produces this data but flags it as a proposed addition rather than smuggling it into the existing schema.
5. **OCR/parse-quality confidence** is not threaded anywhere in the current Contract — handled as log-only for MVP.
