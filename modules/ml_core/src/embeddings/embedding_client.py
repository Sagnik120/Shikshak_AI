import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EmbeddingClient:
    """Wrapper for local sentence-transformers model to compute similarity."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        
    def _load_model(self):
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
            except ImportError:
                logger.error("sentence-transformers is not installed. Run: pip install sentence-transformers")
                raise
                
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts."""
        self._load_model()
        from sentence_transformers import util
        embeddings1 = self.model.encode(text1, convert_to_tensor=True)
        embeddings2 = self.model.encode(text2, convert_to_tensor=True)
        cosine_scores = util.cos_sim(embeddings1, embeddings2)
        return float(cosine_scores[0][0])

_client = EmbeddingClient()

def get_similarity(text1: str, text2: str) -> float:
    return _client.compute_similarity(text1, text2)
