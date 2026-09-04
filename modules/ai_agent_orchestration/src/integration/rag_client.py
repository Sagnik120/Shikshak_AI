from typing import List, Optional
from modules.rag.src.service import RAGService
from modules.rag.src.models import Chunk

class RAGClient:
    """Wrapper calling the existing RAGService."""
    
    def __init__(self, rag_service: Optional[RAGService] = None):
        self.rag = rag_service or RAGService()
        
    def retrieve_context(self, document_id: str, concept: str) -> List[Chunk]:
        result = self.rag.retrieve_context(document_id, concept)
        return result.chunks
