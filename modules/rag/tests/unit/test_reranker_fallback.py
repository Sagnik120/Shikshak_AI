"""With RERANKER_ENABLED=false (the small-host profile) scores must stay on the
scale the retriever's 0.5001 / 0.52 thresholds were calibrated for."""
from modules.rag.src.parsing.structure import extract_key_terms_tfidf
from modules.rag.src.retrieval.reranker import BGEReranker, lexical_relevance

RELEVANCE, CONFIDENT = 0.5001, 0.52
CHUNK = ("For every action there is an equal and opposite reaction. When a rocket expels "
         "exhaust gas downward, the gas pushes the rocket upward.")


def test_matching_chunk_clears_the_confidence_threshold_despite_plurals():
    assert lexical_relevance("rocket actions and reactions", CHUNK, 0.8) >= CONFIDENT


def test_partial_topical_overlap_still_grounds():
    # "laws" vs "law", generic framing words: the old raw-count scorer gave 0.41.
    text = "Newton's first law: an object in motion stays in motion."
    assert lexical_relevance("mechanics equations newton laws motion", text, 0.8) >= CONFIDENT


def test_unrelated_chunk_stays_below_relevance_even_with_high_dense_score():
    assert lexical_relevance("photosynthesis chlorophyll", CHUNK, 0.95) <= RELEVANCE


def test_stopwords_alone_never_count_as_overlap():
    assert lexical_relevance("what is the a an of", CHUNK, 0.9) == 0.0


def test_fallback_rerank_orders_by_relevance(monkeypatch):
    monkeypatch.setenv("RERANKER_ENABLED", "false")
    ranked = BGEReranker().rerank(
        "rocket reaction",
        [{"chunk_id": "a", "text": "Inertia keeps objects at rest.", "score": 0.03, "dense_score": 0.8},
         {"chunk_id": "b", "text": CHUNK, "score": 0.01, "dense_score": 0.8}],
        top_k=2,
    )
    assert [c["chunk_id"] for c in ranked] == ["b", "a"]


def test_key_terms_contain_no_stopwords_or_stopword_bigrams():
    text = ("An object at rest stays at rest. You can see one object move when a force acts.\n\n"
            "Force changes motion. The object accelerates when you push it with force.\n\n"
            "Inertia resists changes in motion. One object with more mass has more inertia.")
    terms = extract_key_terms_tfidf(text)
    junk = {"an", "one", "you", "the", "when", "can", "with"}
    assert terms and not [t for t in terms if set(t.split()) & junk]
