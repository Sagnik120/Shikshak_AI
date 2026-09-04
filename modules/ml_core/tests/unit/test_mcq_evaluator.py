from unittest.mock import patch
from modules.ml_core.src.answer_evaluation.mcq_evaluator import evaluate_mcq

def test_mcq_evaluator_correct():
    raw_answer = "  Option A  "
    expected = "Option A"
    assert evaluate_mcq(raw_answer, expected) is True

def test_mcq_evaluator_incorrect():
    raw_answer = "Option B"
    expected = "Option A"
    assert evaluate_mcq(raw_answer, expected) is False

@patch("modules.ml_core.src.adapters.llm_adapter_client.LLMAdapter.complete")
@patch("modules.ml_core.src.embeddings.embedding_client.EmbeddingClient.compute_similarity")
def test_mcq_evaluator_no_llm_or_embeddings(mock_sim, mock_llm):
    # Proves MCQ strictly avoids LLM and embeddings
    evaluate_mcq("A", "A")
    mock_sim.assert_not_called()
    mock_llm.assert_not_called()
