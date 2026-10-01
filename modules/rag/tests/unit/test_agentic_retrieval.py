"""Offline tests for the bounded agentic retrieval loop.

No embeddings, no vector store, no network: `retrieve_context` is stubbed so the
loop's own control flow — sufficiency, cap enforcement and fallback — is what is
under test.
"""
import pytest

from modules.rag.src.models import RetrievedChunk, RetrievalResult
from modules.rag.src.service import RAGService


def _result(query: str, *, sufficient: bool, score: float = 0.9, chunks: int = 2) -> RetrievalResult:
    return RetrievalResult(
        document_id="doc-1",
        query_text=query,
        chunks=[
            RetrievedChunk(chunk_id=f"c{i}", text=f"chunk {i}", score=score)
            for i in range(chunks)
        ],
        has_sufficient_context=sufficient,
        risk_level="low" if sufficient else "high_hallucination_risk",
    )


class StubService(RAGService):
    """RAGService with only retrieve_context replaced, so the loop is real."""

    def __init__(self, outcomes):
        # Deliberately skips RAGService.__init__ — no models are loaded.
        self._outcomes = list(outcomes)
        self.queries = []

    def retrieve_context(self, document_id=None, query_text="", **kwargs):
        self.queries.append(query_text)
        sufficient = self._outcomes.pop(0) if self._outcomes else False
        if not document_id:
            return RetrievalResult(
                document_id=None, query_text=query_text, chunks=[],
                has_sufficient_context=False, risk_level="no_document_context",
            )
        return _result(query_text, sufficient=sufficient)


def test_a_sufficient_first_pass_is_returned_untouched():
    svc = StubService([True])
    out = svc.retrieve_context_agentic(document_id="doc-1", query_text="Newton's First Law")

    assert len(svc.queries) == 1, "a grounded first pass must not trigger refinement"
    assert out.attempts == 1
    assert out.refined_query is None


def test_an_insufficient_first_pass_is_refined_once_and_kept_when_it_grounds():
    svc = StubService([False, True])
    out = svc.retrieve_context_agentic(
        document_id="doc-1",
        query_text="Introduction to the Cell and Cell Membrane",
        topic="Cell Structure",
    )

    assert len(svc.queries) == 2
    assert out.has_sufficient_context
    assert out.attempts == 2
    assert out.refined_query is not None
    # Framing words are dropped; document vocabulary and the topic survive.
    assert "introduction" not in out.refined_query
    assert "cell" in out.refined_query
    assert "structure" in out.refined_query
    # The caller's original query stays visible for display/caching.
    assert out.query_text == "Introduction to the Cell and Cell Membrane"


def test_falls_back_to_the_single_pass_result_when_refinement_does_not_help():
    svc = StubService([False, False])
    out = svc.retrieve_context_agentic(
        document_id="doc-1", query_text="quantum chromodynamics", topic="Physics"
    )

    assert not out.has_sufficient_context
    assert out.risk_level == "high_hallucination_risk"
    assert out.refined_query is None, "an unhelpful refinement must not be reported as grounding"


def test_the_loop_never_exceeds_its_cap():
    # Never satisfied: the loop must still stop at 1 + MAX_REFINEMENTS passes.
    svc = StubService([False] * 10)
    svc.retrieve_context_agentic(document_id="doc-1", query_text="alpha beta", topic="gamma")

    assert len(svc.queries) == 1 + RAGService.MAX_REFINEMENTS


def test_refinement_can_be_disabled_restoring_exact_single_pass_behaviour():
    svc = StubService([False] * 5)
    out = svc.retrieve_context_agentic(
        document_id="doc-1", query_text="anything", max_refinements=0
    )

    assert len(svc.queries) == 1
    assert out.attempts == 1


def test_topic_only_mode_is_never_refined():
    """No document means nothing to search; this path must be untouched."""
    svc = StubService([])
    out = svc.retrieve_context_agentic(document_id=None, query_text="Newton's Laws")

    assert len(svc.queries) == 1
    assert out.risk_level == "no_document_context"
    assert out.attempts == 1


def test_refinement_stops_when_it_would_repeat_the_same_query():
    """Already-minimal queries refine to themselves — no pointless second pass."""
    svc = StubService([False, False])
    svc.retrieve_context_agentic(document_id="doc-1", query_text="photosynthesis")

    assert svc.queries == ["photosynthesis"]


@pytest.mark.parametrize("topic", [None, "", "Physics"])
def test_refinement_is_deterministic(topic):
    """Same inputs must always produce the same refined query (no LLM in the loop)."""
    svc = RAGService.__new__(RAGService)
    first = svc._refine_query("Introduction to Newton's Second Law of Motion", topic)
    second = svc._refine_query("Introduction to Newton's Second Law of Motion", topic)
    assert first == second
