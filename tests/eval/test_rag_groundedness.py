"""Groundedness, Faithfulness, and Anti-Hallucination Evaluation Suite for RAG & Video.

Directly addresses:
1. Issue 4 from 01_rag_module_fix_plan.md:
   - Evaluates grounded retrieval against in-scope questions.
   - Evaluates defensive hallucination flagging on out-of-scope questions.
   - Verifies explicit anti-hallucination disclaimers in prompt context.
2. Issue 5 from 01_rag_module_fix_plan.md:
   - Verifies diagnostic warnings when scanned/minimal-text documents are ingested.
3. Real-World Live Presentation Pipeline Verification:
   - End-to-end integration test producing an actual MP4 video with real Edge-TTS and static FFmpeg!
"""

import os
import pytest
from modules.rag.src.service import RAGService
from modules.rag.src.indexing.chroma_adapter import ChromaVectorStoreAdapter
from modules.rag.src.parsing.parser import parse_document
from modules.avatar_voice.src.models import TeachingSegment, VisualSpec
from modules.avatar_voice.src.service import AvatarVoiceService
from tests.fixtures.sample_docs import get_physics_notes_markdown


class TestRAGFaithfulnessAndGroundednessEval:
    """Evaluation suite testing grounded retrieval, hallucination defense, and demo readiness."""

    @pytest.fixture
    def rag_service(self):
        vector_store = ChromaVectorStoreAdapter(persist_dir=":memory:")
        return RAGService(vector_store=vector_store)

    @pytest.fixture
    def physics_document(self, rag_service):
        """Ingests a verified physics textbook chapter on Ohm's Law and Mechanics."""
        md_bytes = get_physics_notes_markdown().encode("utf-8")
        doc = rag_service.ingest_document(
            file_bytes=md_bytes,
            filename="physics_grounding_eval.md",
            mime_type="text/markdown"
        )
        return doc

    # =========================================================================
    # 1. IN-SCOPE GROUNDING & FAITHFULNESS EVALUATION
    # =========================================================================

    @pytest.mark.parametrize("query,expected_keyword", [
        ("What is Ohm's law and how is resistance defined?", "resistance"),
        ("What is the formula relating voltage, current, and resistance?", "v = i * r"),
        ("What is Joule's law of heating and electrical power?", "joule's law"),
    ])
    def test_in_scope_queries_are_grounded_with_high_confidence(
        self, rag_service, physics_document, query, expected_keyword
    ):
        """In-scope questions must retrieve grounded chunks with risk_level='low' and cited chunk IDs."""
        result = rag_service.retrieve_context(
            document_id=physics_document.document_id,
            query_text=query,
            top_k=3,
            relevance_threshold=0.2
        )

        assert result.has_sufficient_context is True
        assert result.risk_level == "low"
        assert len(result.chunks) > 0

        # Verify retrieved content contains relevant answer keywords
        combined_text = " ".join(c.text.lower() for c in result.chunks)
        assert expected_keyword in combined_text

        # Verify prompt block formatting contains candidate chunk IDs
        grounded_ctx = rag_service.get_grounded_prompt(
            document_id=physics_document.document_id,
            query_text=query
        )
        assert grounded_ctx.has_sufficient_context is True
        assert len(grounded_ctx.candidate_chunk_ids) > 0
        assert "you are teaching using only the following source material" in grounded_ctx.formatted_prompt_context.lower()

    # =========================================================================
    # 2. OUT-OF-SCOPE ANTI-HALLUCINATION DEFENSE
    # =========================================================================

    @pytest.mark.parametrize("out_of_scope_query", [
        "Explain the light-dependent reactions of photosynthesis in chloroplasts.",
        "How do query, key, and value attention heads work in transformer neural networks?",
        "What is the capital city of Australia and its current GDP?",
    ])
    def test_out_of_scope_queries_flag_high_hallucination_risk(
        self, rag_service, physics_document, out_of_scope_query
    ):
        """Out-of-scope questions must be detected and flagged with high_hallucination_risk.

        Ensures the system adheres to Spec §3: 'minimize unsupported or hallucinated information'.
        """
        # Threshold 0.55 filters out neutral/irrelevant chunks from a physics doc
        result = rag_service.retrieve_context(
            document_id=physics_document.document_id,
            query_text=out_of_scope_query,
            top_k=3,
            relevance_threshold=0.55
        )

        assert result.has_sufficient_context is False
        assert result.risk_level == "high_hallucination_risk"

        grounded_ctx = rag_service.get_grounded_prompt(
            document_id=physics_document.document_id,
            query_text=out_of_scope_query,
            relevance_threshold=0.55
        )
        assert grounded_ctx.has_sufficient_context is False
        assert grounded_ctx.risk_flag == "low_context_fallback_to_general_knowledge"

        prompt_str = grounded_ctx.formatted_prompt_context
        assert "no high-confidence document excerpts found" in prompt_str.lower()
        assert "general knowledge, not from the uploaded document" in prompt_str.lower()
        assert "grounded_on: []" in prompt_str

    # =========================================================================
    # 3. SCANNED PDF / MINIMAL TEXT WARNING DETECTION (Issue R5)
    # =========================================================================

    def test_scanned_minimal_text_document_produces_warning(self):
        """Minimal text / scanned image documents must populate ParsedDocument.warnings."""
        # Simulated scanned PDF bytes with almost no text (< 30 characters) but > 200 bytes payload
        dummy_scanned_bytes = b"%PDF-1.4 \x00\x01\x02\x03\xff\xfe\x00\x01\x02" * 40
        parsed = parse_document(
            file_bytes=dummy_scanned_bytes,
            filename="scanned_handwritten_notes.pdf",
            mime_type="application/pdf"
        )
        # Verify warnings populated so frontend/orchestrator can alert student
        assert isinstance(parsed.warnings, list)
        assert len(parsed.warnings) > 0
        assert any("scanned" in w.lower() or "minimal" in w.lower() for w in parsed.warnings)

    # =========================================================================
    # 4. LIVE DEMO PIPELINE: PROGRESSIVE VIDEO GENERATION WITH REAL FFMPEG
    # =========================================================================

    def test_live_demo_full_pipeline_progressive_video_synthesis(self, tmp_path):
        """End-to-End Live Demo Test: Math Derivation with real FFmpeg video synthesis."""
        out_dir = str(tmp_path)
        service = AvatarVoiceService(output_dir=out_dir)

        segment = TeachingSegment(
            node_id="demo_final_quadratic",
            script_text="Let us solve x squared minus 4 equals 0. Factoring gives x minus 2 times x plus 2 equals 0, so x is plus or minus 2.",
            language="en",
            visual_spec=VisualSpec(
                type="equation",
                content=r"x^2 - 4 = 0",
                steps=[
                    r"x^2 - 4 = 0",
                    r"(x - 2)(x + 2) = 0",
                    r"x = \pm 2"
                ]
            ),
            avatar_cue="emphasis"
        )

        rendered = service.render_segment_sync(segment)

        assert rendered.node_id == "demo_final_quadratic"
        assert rendered.duration_sec > 0.0
        assert os.path.exists(rendered.video_url)
        assert os.path.getsize(rendered.video_url) > 0
        assert rendered.video_url.endswith(".mp4")
