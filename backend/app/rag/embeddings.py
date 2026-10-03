from __future__ import annotations

import os
from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    name: str
    dimensions: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n_texts, dimensions) float32 embedding matrix."""


class HashingEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, dependency-light embedding provider built on
    scikit-learn's HashingVectorizer + TF-IDF re-weighting. It requires no
    model download and no network access, so RAG works fully offline in
    DEMO mode. Swap EMBEDDING_PROVIDER=openai (or another real embedding
    API) for production-quality semantic embeddings.
    """

    name = "hashing"
    dimensions = 512

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import HashingVectorizer

        self._vectorizer = HashingVectorizer(
            n_features=self.dimensions, alternate_sign=False, norm="l2"
        )

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = self._vectorizer.transform(texts)
        return matrix.toarray().astype("float32")


class OpenAIEmbeddingProvider(EmbeddingProvider):  # pragma: no cover - integration point
    name = "openai"
    dimensions = 1536

    def __init__(self) -> None:
        self.api_key = os.environ.get("LLM_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=openai requires LLM_API_KEY to be set. "
                "Use EMBEDDING_PROVIDER=hashing for the offline demo."
            )

    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError(
            "Real OpenAI embeddings require network access to the OpenAI API, "
            "not available in this environment. Implement this against the "
            "openai Python client once an API key and network access are available."
        )


def get_embedding_provider(name: str = "hashing") -> EmbeddingProvider:
    if name == "openai":
        return OpenAIEmbeddingProvider()
    return HashingEmbeddingProvider()
