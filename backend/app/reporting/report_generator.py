from __future__ import annotations

import datetime as dt

from app.config import get_settings
from app.rag.generator import get_llm_provider
from app.rag.retriever import get_retriever
from app.reporting.schemas import EvidenceItem, ReportOut

_STANDARD_LIMITATIONS = [
    "This system does not claim to identify every piece of ghost gear or marine debris present in an area.",
    "The drift result is a forecast/probability zone, not an exact guaranteed future trajectory.",
    "The risk score is a decision-support score, not a certified ground-truth ecological probability.",
    "Detections are DEMO/UNVERIFIED unless a human has explicitly marked them VERIFIED or RECOVERED.",
]


def generate_report(
    detection: dict,
    drift_summary: dict,
    geospatial_summary: dict,
    risk_summary: dict,
    priority_summary: dict,
) -> ReportOut:
    """
    Assemble the final evidence-based report. The narrative text is
    produced by the configured LLMProvider (deterministic MockLLMProvider
    by default) but every numeric fact (risk score, geospatial overlap,
    forecast positions) is passed in already computed - the LLM only
    narrates, it never invents or recalculates facts.
    """
    settings = get_settings()
    retriever = get_retriever()
    llm = get_llm_provider(settings.LLM_PROVIDER)

    query = (
        f"{detection.get('object_class', '')} risk near "
        f"{'protected area' if geospatial_summary.get('protected_area_overlap') else 'open water'} "
        f"{'habitat overlap' if geospatial_summary.get('habitat_overlap') else ''}"
    ).strip()
    retrieval = retriever.retrieve(query, top_k=4)

    narrative = llm.generate_narrative(
        detection_summary=detection,
        risk_summary=risk_summary,
        priority_summary=priority_summary,
        retrieval=retrieval,
    )

    evidence = [EvidenceItem(text=c.text, source=c.source, score=c.score) for c in retrieval.chunks]

    return ReportOut(
        detection_id=detection["external_id"],
        generated_at=dt.datetime.utcnow(),
        summary=narrative,
        detection=detection,
        forecast=drift_summary,
        risk={**risk_summary, **geospatial_summary},
        reasons=risk_summary.get("reason_codes", []),
        recommended_action=priority_summary.get("recommended_action", ""),
        evidence=evidence,
        limitations=_STANDARD_LIMITATIONS,
    )
