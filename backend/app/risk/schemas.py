from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import RiskLevel


class RiskAssessmentOut(BaseModel):
    detection_id: str
    risk_score: float
    risk_level: RiskLevel
    feature_values: dict[str, float]
    feature_contributions: dict[str, float]
    reason_codes: list[str]
