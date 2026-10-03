from __future__ import annotations

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    text: str
    source: str
    score: float


class RetrievalResult(BaseModel):
    query: str
    chunks: list[RetrievedChunk]

    @property
    def has_evidence(self) -> bool:
        return len(self.chunks) > 0
