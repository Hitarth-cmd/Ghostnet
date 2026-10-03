from __future__ import annotations

import os
from abc import ABC, abstractmethod

from app.rag.schemas import RetrievalResult


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def generate_narrative(
        self,
        detection_summary: dict,
        risk_summary: dict,
        priority_summary: dict,
        retrieval: RetrievalResult,
    ) -> str:
        """Produce a short narrative paragraph explaining the (already
        computed) risk/priority result, citing retrieved evidence. Must
        NEVER recompute the risk score - only explain it."""


class MockLLMProvider(LLMProvider):
    """
    Deterministic, template-driven narrative generator. Requires no API
    key and no network access, so report generation works fully offline.
    Produces the same text for the same inputs every time.
    """

    name = "mock"

    def generate_narrative(
        self,
        detection_summary: dict,
        risk_summary: dict,
        priority_summary: dict,
        retrieval: RetrievalResult,
    ) -> str:
        object_class = detection_summary.get("object_class", "unknown_floating_object").replace("_", " ")
        confidence_pct = round(detection_summary.get("confidence", 0.0) * 100, 1)
        risk_level = risk_summary.get("risk_level", "LOW")
        risk_score = risk_summary.get("risk_score", 0.0)
        reasons = risk_summary.get("reason_codes", [])
        priority_level = priority_summary.get("priority_level", "LOW")

        lines = [
            f"A {object_class} detection ({confidence_pct}% model confidence, DEMO/UNVERIFIED unless "
            f"otherwise marked) was assessed at {risk_level} ecological risk (score {risk_score}).",
        ]

        if reasons:
            reason_text = ", ".join(r.replace("_", " ") for r in reasons)
            lines.append(f"Contributing factors: {reason_text}.")

        lines.append(
            f"This corresponds to a {priority_level} monitoring priority. "
            f"{priority_summary.get('recommended_action', '')}"
        )

        if retrieval.has_evidence:
            top_sources = sorted({c.source for c in retrieval.chunks})
            lines.append(
                "Supporting general context was retrieved from: " + ", ".join(top_sources) + "."
            )
        else:
            lines.append("Insufficient retrieved evidence.")

        lines.append(
            "This is a decision-support assessment, not a certified ecological determination; "
            "the forecast trajectory and uncertainty zone represent a probability estimate, not a "
            "guaranteed future position."
        )
        return " ".join(lines)


class OpenAICompatibleLLMProvider(LLMProvider):  # pragma: no cover - integration point
    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.environ.get("LLM_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "LLM_PROVIDER=openai requires LLM_API_KEY to be set. "
                "Use LLM_PROVIDER=mock for the offline demo."
            )

    def generate_narrative(self, detection_summary, risk_summary, priority_summary, retrieval) -> str:
        raise NotImplementedError(
            "Real LLM narration requires network access to an LLM API, not available in "
            "this environment. Implement this against your chosen provider's client once "
            "an API key and network access are available. The risk score itself must "
            "continue to come from app/risk/risk_engine.py, never from this method."
        )


def get_llm_provider(name: str = "mock") -> LLMProvider:
    if name in ("openai", "anthropic"):
        return OpenAICompatibleLLMProvider()
    return MockLLMProvider()
