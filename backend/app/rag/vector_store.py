from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class VectorRecord:
    id: str
    text: str
    source: str
    embedding: np.ndarray
    metadata: dict = field(default_factory=dict)


class VectorStore(ABC):
    @abstractmethod
    def add(self, records: list[VectorRecord]) -> None: ...

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[VectorRecord, float]]: ...

    @abstractmethod
    def count(self) -> int: ...


class InMemoryVectorStore(VectorStore):
    """Plain numpy cosine-similarity vector store. No external service required."""

    def __init__(self) -> None:
        self._records: list[VectorRecord] = []

    def add(self, records: list[VectorRecord]) -> None:
        self._records.extend(records)

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[VectorRecord, float]]:
        if not self._records:
            return []
        matrix = np.stack([r.embedding for r in self._records])
        q = query_embedding.reshape(1, -1)

        q_norm = np.linalg.norm(q) + 1e-8
        m_norm = np.linalg.norm(matrix, axis=1) + 1e-8
        sims = (matrix @ q.T).flatten() / (m_norm * q_norm)

        top_idx = np.argsort(-sims)[:top_k]
        return [(self._records[i], float(sims[i])) for i in top_idx]

    def count(self) -> int:
        return len(self._records)


class FaissVectorStore(VectorStore):  # pragma: no cover - optional acceleration path
    """Optional FAISS-backed store for larger corpora. Requires faiss-cpu installed."""

    def __init__(self, dimensions: int) -> None:
        import faiss

        self._index = faiss.IndexFlatIP(dimensions)
        self._records: list[VectorRecord] = []

    def add(self, records: list[VectorRecord]) -> None:
        vecs = np.stack([r.embedding for r in records]).astype("float32")
        faiss_norm = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-8)
        self._index.add(faiss_norm)
        self._records.extend(records)

    def search(self, query_embedding: np.ndarray, top_k: int) -> list[tuple[VectorRecord, float]]:
        if not self._records:
            return []
        q = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        scores, idx = self._index.search(q.reshape(1, -1).astype("float32"), min(top_k, len(self._records)))
        return [(self._records[i], float(s)) for s, i in zip(scores[0], idx[0]) if i != -1]

    def count(self) -> int:
        return len(self._records)


def get_vector_store(name: str, dimensions: int) -> VectorStore:
    if name == "faiss":
        try:
            return FaissVectorStore(dimensions)
        except ImportError:
            return InMemoryVectorStore()
    return InMemoryVectorStore()
