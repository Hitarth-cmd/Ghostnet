from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class EvidenceItem(BaseModel):
    text: str
    source: str
    score: float


class ReportOut(BaseModel):
    detection_id: str
    generated_at: dt.datetime
    summary: str
    detection: dict
    forecast: dict
    risk: dict
    reasons: list[str]
    recommended_action: str
    evidence: list[EvidenceItem]
    limitations: list[str]
