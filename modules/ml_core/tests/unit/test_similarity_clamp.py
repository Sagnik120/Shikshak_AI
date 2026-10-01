"""Near-identical texts must not produce a similarity above 1 (float32 rounding)."""
from unittest.mock import MagicMock

import torch

from modules.ml_core.src.embeddings.embedding_client import EmbeddingClient


def test_similarity_is_clamped_to_unit_range():
    client = EmbeddingClient()
    client.model = MagicMock()
    client.model.encode.return_value = torch.tensor([0.1, 0.2, 0.3], dtype=torch.float32)
    # cos_sim of a float32 vector with itself can round to 1.0000001.
    assert client.compute_similarity("same", "same") <= 1.0
