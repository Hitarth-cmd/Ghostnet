from __future__ import annotations

import os
from functools import lru_cache

from app.config import get_settings
from app.rag.chunking import chunk_text
from app.rag.embeddings import get_embedding_provider
from app.rag.ingestion import load_directory
from app.rag.schemas import RetrievalResult, RetrievedChunk
from app.rag.vector_store import VectorRecord, get_vector_store

_KB_ROOT = os.environ.get(
    "GHOSTNET_KNOWLEDGE_BASE",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "knowledge_base"),
)


class Retriever:
    def __init__(self) -> None:
        settings = get_settings()
        self.embedder = get_embedding_provider(settings.EMBEDDING_PROVIDER)
        self.store = get_vector_store(settings.VECTOR_STORE, self.embedder.dimensions)
        self._ingest_knowledge_base()

    def _ingest_knowledge_base(self) -> None:
        if not os.path.isdir(_KB_ROOT):
            return
        docs = load_directory(_KB_ROOT)
        records = []
        for source_path, text in docs:
            chunks = chunk_text(text)
            if not chunks:
                continue
            embeddings = self.embedder.embed(chunks)
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                records.append(
                    VectorRecord(
                        id=f"{os.path.basename(source_path)}::{i}",
                        text=chunk,
                        source=os.path.basename(source_path),
                        embedding=emb,
                    )
                )
        if records:
            self.store.add(records)

    def retrieve(self, query: str, top_k: int = 4) -> RetrievalResult:
        if self.store.count() == 0:
            return RetrievalResult(query=query, chunks=[])
        query_embedding = self.embedder.embed([query])[0]
        results = self.store.search(query_embedding, top_k)
        chunks = [
            RetrievedChunk(text=r.text, source=r.source, score=round(score, 4))
            for r, score in results
            if score > 0.0
        ]
        return RetrievalResult(query=query, chunks=chunks)


@lru_cache
def get_retriever() -> Retriever:
    return Retriever()
