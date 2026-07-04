"""
Embedding Service for SmartRFP

Responsibilities
----------------
1. Load embedding model only once (singleton)
2. Generate document embeddings (batched)
3. Generate query embeddings
4. Report embedding dimension from config
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from langchain_huggingface import HuggingFaceEmbeddings

from backend.config import settings

# This model (all-MiniLM-L6-v2) is public — downloading it without an HF_TOKEN
# is expected and safe. huggingface_hub logs a warning that reads alarmingly
# like an auth failure ("sending unauthenticated requests..."); it isn't one,
# so we drop it to WARNING->ERROR level instead of hiding a real problem.
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)


class EmbeddingService:
    """Wrapper around HuggingFace embeddings."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str = "cpu",
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._dimension = settings.EMBEDDING_DIMENSION

        self.embedding_model = HuggingFaceEmbeddings(
            model_name=self.model_name,
            model_kwargs={"device": device},
            encode_kwargs={
                "normalize_embeddings": True,  # required for cosine metric
                "batch_size": 32,
            },
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self.embedding_model.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        return self.embedding_model.embed_query(query)

    @property
    def dimension(self) -> int:
        """Embedding dimension (must match the Pinecone index dimension)."""
        return self._dimension


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Singleton — loads the model only once per process."""
    return EmbeddingService()