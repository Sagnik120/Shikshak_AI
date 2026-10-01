import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

class EmbeddingClient:
    """Wrapper for local sentence-transformers model to compute similarity."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = None
        self._lock = threading.Lock()

    def _load_model(self):
        # Two threads (the start-up warm-up and a learner's first answer)
        # loading at once crashed PyTorch's GPU backend.
        with self._lock:
            self._load_model_locked()

    def _load_model_locked(self):
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
        # Serialised: concurrent encodes on the GPU backend (several learners
        # graded at once) can crash the process. Each call takes milliseconds.
        with self._lock:
            embeddings1 = self.model.encode(text1, convert_to_tensor=True)
            embeddings2 = self.model.encode(text2, convert_to_tensor=True)
            cosine_scores = util.cos_sim(embeddings1, embeddings2)
        # float32 rounding gives 1.0000001 for (near-)identical texts — e.g. a
        # learner quoting their notes — which failed EvaluationResult's
        # confidence <= 1 check and crashed the live lesson.
        return max(-1.0, min(1.0, float(cosine_scores[0][0])))

_client = EmbeddingClient()

def get_similarity(text1: str, text2: str) -> float:
    return _client.compute_similarity(text1, text2)
