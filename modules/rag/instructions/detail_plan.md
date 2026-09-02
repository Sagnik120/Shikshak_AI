# detail_plan.md — rag

## Goal
Ground lesson generation in the student's uploaded material and minimize hallucination
(15/100 rubric points — second-highest-weighted single area after adaptation).

## Pipeline
1. **Ingestion**: accept parsed text+structure from `ml_core`'s document parser (or own the
   parsing step directly — decide ownership once in Contract, avoid duplicate implementations).
2. **Chunking**: semantic/structure-aware chunking (prefer splitting on headings/slide
   boundaries over fixed-token windows where structure is available) — target ~200-500 tokens/chunk
   with overlap; retain `section_title`/`page_or_slide` metadata for citation.
3. **Embedding**: `sentence-transformers` (e.g. a multilingual embedding model, since uploaded
   docs and teaching language may differ — PS §8 explicitly requires cross-language support:
   "English textbook → Hindi teaching").
4. **Indexing**: vector store (Chroma for hackathon-local; interface behind
   `VectorStoreAdapter` per root Contract §14 so swapping to Qdrant/Pinecone is a config change).
5. **Retrieval**: for each `LessonNode`/`InteractionEvent` needing grounding, retrieve top-k
   chunks by embedding similarity; optionally hybrid with keyword/BM25 for precise term lookups
   (definitions, formulas).
6. **Grounding/citation**: attach retrieved `chunk_id`s to the Explainer Agent's context; the
   Explainer Agent's output can optionally carry a `grounded_on: [chunk_id...]` field (propose
   as Contract extension if adopted) so the system can show "this explanation is based on
   Chapter 4."
7. **Hallucination mitigation**: prompt pattern = "answer only using the provided context; if
   the context is insufficient, say so and fall back to general knowledge explicitly labeled as
   such" — this distinction (grounded vs. general-knowledge) should be surfaced, not hidden.

## Optional web-augmented retrieval (innovation point, PS §18 adjacent)
For topic-only sessions (no upload) or when uploaded material lacks depth for the requested
level, allow retrieval from a curated/general knowledge fallback — clearly labeled in the UI as
"general knowledge" vs. "from your document" to preserve grounding transparency.

## Evaluation
`tests/eval/` must include a groundedness check: sample Q&A pairs where the answer must trace to
a specific chunk; assert the system's answer doesn't introduce facts absent from top-k retrieved
chunks (simple string/entailment-based check is acceptable for hackathon scope).
