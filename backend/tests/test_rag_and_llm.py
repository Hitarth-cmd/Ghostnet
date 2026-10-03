from __future__ import annotations

from app.rag.chunking import chunk_text
from app.rag.embeddings import HashingEmbeddingProvider
from app.rag.generator import MockLLMProvider
from app.rag.retriever import get_retriever
from app.rag.schemas import RetrievalResult, RetrievedChunk


def test_chunking_splits_long_text():
    text = "\n\n".join([f"Paragraph {i} with some content." for i in range(50)])
    chunks = chunk_text(text, chunk_size_chars=200, overlap_chars=20)
    assert len(chunks) > 1
    assert all(len(c) > 0 for c in chunks)


def test_hashing_embedder_is_deterministic():
    embedder = HashingEmbeddingProvider()
    v1 = embedder.embed(["marine debris near coral reef"])
    v2 = embedder.embed(["marine debris near coral reef"])
    assert (v1 == v2).all()
    assert v1.shape[1] == embedder.dimensions


def test_retriever_finds_relevant_chunks():
    retriever = get_retriever()
    result = retriever.retrieve("ghost fishing gear entanglement turtles", top_k=3)
    assert isinstance(result, RetrievalResult)
    assert len(result.chunks) > 0
    assert result.has_evidence


def test_mock_llm_never_fabricates_evidence_when_none_found():
    llm = MockLLMProvider()
    empty_retrieval = RetrievalResult(query="nonsense query", chunks=[])
    narrative = llm.generate_narrative(
        detection_summary={"object_class": "marine_debris", "confidence": 0.5},
        risk_summary={"risk_level": "LOW", "risk_score": 0.1, "reason_codes": []},
        priority_summary={"priority_level": "LOW", "recommended_action": "Routine observation."},
        retrieval=empty_retrieval,
    )
    assert "Insufficient retrieved evidence." in narrative


def test_mock_llm_cites_sources_when_evidence_present():
    llm = MockLLMProvider()
    retrieval = RetrievalResult(
        query="q",
        chunks=[RetrievedChunk(text="some evidence text", source="ghost_gear_overview.md", score=0.9)],
    )
    narrative = llm.generate_narrative(
        detection_summary={"object_class": "suspected_ghost_gear", "confidence": 0.9},
        risk_summary={"risk_level": "HIGH", "risk_score": 0.8, "reason_codes": ["habitat_overlap"]},
        priority_summary={"priority_level": "HIGH", "recommended_action": "Prioritize monitoring."},
        retrieval=retrieval,
    )
    assert "ghost_gear_overview.md" in narrative
    assert "Insufficient retrieved evidence" not in narrative
