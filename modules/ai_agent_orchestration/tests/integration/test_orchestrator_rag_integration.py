from unittest.mock import MagicMock
from modules.ai_agent_orchestration.src.integration.rag_client import RAGClient
from modules.rag.src.models import RetrievalResult, RetrievedChunk

def test_rag_integration_mock():
    mock_rag_service = MagicMock()
    mock_result = RetrievalResult(
        document_id="doc_123",
        query_text="test concept",
        chunks=[RetrievedChunk(chunk_id="c1", text="mocked rag text", score=0.99)]
    )
    mock_rag_service.retrieve_context.return_value = mock_result
    
    client = RAGClient(rag_service=mock_rag_service)
    chunks = client.retrieve_context("doc_123", "test concept")
    
    assert len(chunks) == 1
    assert chunks[0].text == "mocked rag text"
    mock_rag_service.retrieve_context.assert_called_once_with("doc_123", "test concept")
