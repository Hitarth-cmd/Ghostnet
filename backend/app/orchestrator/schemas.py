from __future__ import annotations

from pydantic import BaseModel

from app.drift.schemas import DriftResult
from app.reporting.schemas import ReportOut


class AnalysisResult(BaseModel):
    detection_id: str
    drift: DriftResult
    geospatial: dict
    risk: dict
    priority: dict
    report: ReportOut
